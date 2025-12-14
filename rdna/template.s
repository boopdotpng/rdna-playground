.amdgcn_target "amdgcn-amd-amdhsa--[[arch]]"
.amdhsa_code_object_version 5

.text
.globl my_kernel
.p2align 8
.type my_kernel,@function
my_kernel:
  [[code]]
  .size my_kernel, .-my_kernel

.rodata
.p2align 6
.amdhsa_kernel my_kernel
  .amdhsa_user_sgpr_kernarg_segment_ptr 1
  .amdhsa_kernarg_size [[kernarg_size]]
  .amdhsa_wavefront_size32 1        
  .amdhsa_next_free_vgpr .amdgcn.next_free_vgpr
  .amdhsa_next_free_sgpr .amdgcn.next_free_sgpr
.end_amdhsa_kernel

.amdgpu_metadata
---
amdhsa.version:
  - 1
  - 2
amdhsa.target: "amdgcn-amd-amdhsa--[[arch]]"   
amdhsa.kernels:
  - .name: my_kernel
    .symbol: my_kernel.kd
    .language: Assembler
    .kernarg_segment_size: [[kernarg_size]]
    .group_segment_fixed_size: 0
    .private_segment_fixed_size: 0
    .kernarg_segment_align: [[kernarg_align]]
    .wavefront_size: 32
    .sgpr_count: [[sgpr_count]]
    .vgpr_count: [[vgpr_count]]
    .max_flat_workgroup_size: 256
    .args:
[[args_yaml]]
.end_amdgpu_metadata
