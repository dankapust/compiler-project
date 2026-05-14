from enum import Enum


class Register(Enum):
    RAX = "rax"
    RBX = "rbx"
    RCX = "rcx"
    RDX = "rdx"
    RSI = "rsi"
    RDI = "rdi"
    RBP = "rbp"
    RSP = "rsp"
    R8 = "r8"
    R9 = "r9"
    R10 = "r10"
    R11 = "r11"
    R12 = "r12"
    R13 = "r13"
    R14 = "r14"
    R15 = "r15"
    XMM0 = "xmm0"
    XMM1 = "xmm1"
    XMM2 = "xmm2"
    XMM3 = "xmm3"
    XMM4 = "xmm4"
    XMM5 = "xmm5"
    XMM6 = "xmm6"
    XMM7 = "xmm7"



INTEGER_PARAM_REGISTERS = [
    Register.RDI,
    Register.RSI,
    Register.RDX,
    Register.RCX,
    Register.R8,
    Register.R9,
]

FLOAT_PARAM_REGISTERS = [
    Register.XMM0,
    Register.XMM1,
    Register.XMM2,
    Register.XMM3,
    Register.XMM4,
    Register.XMM5,
    Register.XMM6,
    Register.XMM7,
]

CALLER_SAVED_REGISTERS = [
    Register.RAX,
    Register.RCX,
    Register.RDX,
    Register.RSI,
    Register.RDI,
    Register.R8,
    Register.R9,
    Register.R10,
    Register.R11,
]

CALLEE_SAVED_REGISTERS = [
    Register.RBX,
    Register.R12,
    Register.R13,
    Register.R14,
    Register.R15,
]

RETURN_REGISTER = Register.RAX
FLOAT_RETURN_REGISTER = Register.XMM0
