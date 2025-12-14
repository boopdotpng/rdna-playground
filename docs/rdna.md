# rdna3.5 (but generally most of rdna) docs

After you create the initial basic hsaco object (with `s_endpgm` as the only instruction), we now have to figure out how to actually write RDNA. All the examples in this repository were tested on an RDNA3.5 integrated GPU, but they should also work on RDNA4 and RDNA3 cards as well. As we read the ISA pdf for each architecture, we'll learn which instructions were introduced in which architectures and how they've changed. 

Essentially, we're writing the kernel code -- originally HIP or CUDA -- as RDNA assembly. 

## rdna3.5 architecture
Some of this will apply to all AMD gpus. Since most people are already familiar with CUDA terms, I will try to use those where possible. 


## basics / setup 

**Vocabulary**
1. 

### passing in kernel arguments 


### sgprs and vgprs (registers)


### launch size (locals and globals)



## a simple program
