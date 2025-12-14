import os
os.environ["DEBUG"] = "5"
from tinygrad import Device
from tinygrad.device import Buffer
from tinygrad.dtype import dtypes
from pathlib import Path 
import subprocess
from dataclasses import dataclass
from typing import Literal, Optional
from dataclasses import dataclass
from typing import Optional, Literal

# just AMD works if you have 1 gpu, otherwise enumerate them
# gpu is used later to allocate buffers, make sure they're on the same device
gpu = "AMD:0"
dev = Device[gpu]
arch = dev.arch 

@dataclass
class KernArg:
  name: str
  size: int
  align: int
  value_kind: Literal["by_value", "global_buffer"]
  type_name: Optional[str] = None
  address_space: Optional[Literal["global","local","constant","private","generic","region"]] = None
  actual_access: Optional[Literal["read_only","write_only","read_write"]] = None
  is_const: Optional[bool] = None

def _align_up(x: int, a: int) -> int:
  return (x + (a-1)) & ~(a-1)

def build_args_yaml(args: list[KernArg], base_indent: int = 6):
  off = 0
  max_align = 1
  lines = []
  ind = " " * base_indent
  ind2 = " " * (base_indent + 2)

  for a in args:
    off = _align_up(off, a.align)
    max_align = max(max_align, a.align)

    lines.append(f"{ind}- .name: {a.name}")
    if a.type_name:      lines.append(f"{ind2}.type_name: {a.type_name}")
    lines.append(f"{ind2}.size: {a.size}")
    lines.append(f"{ind2}.offset: {off}")
    lines.append(f"{ind2}.value_kind: {a.value_kind}")

    if a.value_kind == "global_buffer":
      lines.append(f"{ind2}.address_space: {a.address_space or 'global'}")
      if a.actual_access: lines.append(f"{ind2}.actual_access: {a.actual_access}")
      if a.is_const is not None:
        lines.append(f"{ind2}.is_const: {'true' if a.is_const else 'false'}")

    off += a.size

  kernarg_size = _align_up(off, max_align)
  return ("\n".join(lines) if lines else f"{ind}[]"), kernarg_size, max_align


def build_hsaco(path: Path, args_yaml, kernarg_size, kernarg_align) -> bool:
  global arch
  template = open(path/"template.s").read()
  raw_rdna = open(path/"kernel.s").read()

  template = template.replace("[[arch]]", arch)

  template = template.replace("[[code]]", raw_rdna)

  template = template.replace("[[args_yaml]]", args_yaml)
  template = template.replace("[[kernarg_size]]", str(kernarg_size))
  template = template.replace("[[kernarg_align]]", str(kernarg_align))

  # for now, pick integers (later you can refine)
  template = template.replace("[[sgpr_count]]", "32")
  template = template.replace("[[vgpr_count]]", "32")

  open(path/"final.s", 'w').write(template)

  try:
    subprocess.run([
      "llvm-mc",
      "-triple=amdgcn-amd-amdhsa",
      f"-mcpu={arch}",
      "-filetype=obj",
      path/"final.s",
      "-o", path/"kernel.o"
    ], check=True, env=os.environ.copy())

    subprocess.run([
      "ld.lld",
      "-shared",
      path/"kernel.o",
      "-o", path/"kernel.hsaco"
    ])
  except Exception as e:
    print(e)
    return False

  return True

if __name__ == "__main__":
  # set up input parameters here
  N = 8 
  a = Buffer(gpu, N, dtypes.float32).allocate()
  out = Buffer(gpu, N, dtypes.float32).allocate()

  # optionally, load in data
  import numpy as np 
  a.copyin(memoryview(np.arange(N, dtype=np.float32)))

  # make sure these args match the above args. soon, we will auto-generate them from the above Buffers
  args = [
    KernArg("a", size=8, align=8, value_kind="global_buffer", type_name="float*", actual_access="read_only"),
    KernArg("out", size=8, align=8, value_kind="global_buffer", type_name="float*", actual_access="write_only")
  ]
  args_yaml, kernarg_size, kernarg_align = build_args_yaml(args)

  wd = Path(__file__).parent/Path("rdna")
  if not build_hsaco(wd, args_yaml, kernarg_size, kernarg_align): exit(0)

  # load hsaco 
  lib = (wd/"kernel.hsaco").read_bytes()
  prg = dev.runtime(wd/"my_kernel", lib)

  # kernel launch parameters 
  local = (N, 1, 1) # threads per workgroup; cuda equivalent is block
  global_ = (8, 1, 1) # workgroups; cuda equivalent is grid 
  
  # execute
  prg(a._buf, out._buf, global_size=global_, local_size=local, wait=True)

  # read back
  res = np.frombuffer(out.as_buffer(), dtype=np.float32)
  print("a:    ", np.frombuffer(a.as_buffer(), dtype=np.float32))
  print("a + 1:", res)