#include <hip/hip_runtime.h>
#include <vector>
#include <numeric>
#include <cstdio>

__global__ void add1(float *x, float *out, int n) {
  int i = (int) (blockIdx.x * blockDim.x + threadIdx.x);
  if (i < n) out[i] = x[i] + 1.0f;
}

int main() {
  constexpr int N = 16; 

  std::vector<float> h_in(N); 
  std::iota(h_in.begin(), h_in.end(), 0.0f);

  float *d = nullptr; 
  float *d_out = nullptr;
  hipMalloc(&d, N*sizeof(float)); 
  hipMalloc(&d_out, N*sizeof(float)); 

  hipMemcpy(d, h_in.data(), N*sizeof(float), hipMemcpyHostToDevice);

  dim3 block(64); 
  dim3 grid((N+block.x-1)/block.x);

  hipLaunchKernelGGL(add1, grid, block, 0, 0, d, d_out, N); 
  hipDeviceSynchronize(); 

  // copy back,
  auto output = std::vector<float>(N);
  hipMemcpy(output.data(), d_out, N*sizeof(float), hipMemcpyDeviceToHost);

  for (auto i: h_in) std::printf("%.1f, ", i);
  std::printf("\n");
  for(auto i: output) std::printf("%.1f, ", i);

  std::printf("\n");

  hipFree(d);
  hipFree(d_out);
  return 0;
}
