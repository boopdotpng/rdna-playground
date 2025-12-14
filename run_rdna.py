import os
os.environ["DEBUG"] = "5"
from tinygrad import Device
from tinygrad.device import Buffer
from tinygrad.dtype import dtypes
from pathlib import Path 
import subprocess

# just AMD works if you have 1 gpu, otherwise enumerate them
# gpu is used later to allocate buffers, make sure they're on the same device
gpu = "AMD:0"
dev = Device[gpu]
arch = dev.arch 

def build_hsaco(path: Path, args_yaml: str = "", kernarg_size: int = 0, kernarg_align: int = 16) -> bool:
  global arch
  template = open(path/"template.hsaco").read()
  raw_rdna = open(path/"kernel.s").read()

  template = template.replace("[[arch]]", arch)

  template = template.replace("[[code]]", raw_rdna)

  template = template.replace("[[args_yaml]]", args_yaml)
  template = template.replace("[[kernarg_size]]", str(kernarg_size))
  template = template.replace("[[kernarg_align]]", str(kernarg_align))

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
    ], check=True)
  except Exception as e:
    print(e)
    return False
  return True

if __name__ == "__main__":
  # set up input parameters here
  N = 16
  a = Buffer(gpu, N, dtypes.float32).allocate()
  out = Buffer(gpu, N, dtypes.float32).allocate()

  # optionally, load in data
  import numpy as np 
  a.copyin(memoryview(np.arange(N, dtype=np.float32)))

  # make sure these args match the above args. soon, we will auto-generate them from the above Buffers

  wd = Path(__file__).parent/Path("rdna")
  if not build_hsaco(wd, kernarg_size=16, kernarg_align=16): exit(0)

  # load hsaco 
  lib = (wd/"kernel.hsaco").read_bytes()

  # find kernel name in object
  prg = dev.runtime(name="my_kernel", lib=lib)

  # kernel launch parameters 
  local = (N, 1, 1) # threads per workgroup; cuda equivalent is block
  global_ = (N, 1, 1) # workgroups; cuda equivalent is grid 
  
  # execute
  prg(a._buf, out._buf, global_size=global_, local_size=local, wait=True)

  # read back
  res = np.frombuffer(out.as_buffer(), dtype=np.float32)
  print("a:    ", np.frombuffer(a.as_buffer(), dtype=np.float32))
  print("a + 1:", res)
