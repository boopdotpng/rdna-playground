// kernarg ptr is in s[0:1] because we only enabled kernarg_segment_ptr
// load a_ptr (arg0) and out_ptr (arg1)
s_load_dwordx2 s[2:3], s[0:1], 0x0    // a_ptr
s_load_dwordx2 s[4:5], s[0:1], 0x8    // out_ptr
s_waitcnt lgkmcnt(0)

// byte_offset = tid_x * 4 (float32)
v_lshlrev_b32 v1, 2, v0

// v4 = a[tid_x]
global_load_dword v4, v1, s[2:3]
s_waitcnt vmcnt(0)

// v4 = v4 + 1.0f
v_add_f32 v4, 1.0, v4

// out[tid_x] = v4
global_store_dword v1, v4, s[4:5]
s_endpgm
