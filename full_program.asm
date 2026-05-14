bits 64

section .text
extern print_int
extern print_string
extern read_int
extern exit

global add
add:
    push rbp
    mov rbp, rsp
    mov [rbp-8], rdi
    mov [rbp-16], rsi
entry_add_1:
    mov rax, [rbp-8]
    mov [rbp-24], rax
    mov rax, [rbp-16]
    mov [rbp-32], rax
    movsx rax, dword [rbp-24]
    mov [rbp-16], rax
    mov rax, [rbp-16]
    pop rbp
    ret

global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 64
entry_main_3:
    mov rax, 5
    mov [rbp-8], rax
    mov rax, 10
    mov [rbp-16], rax
    movsx rax, dword [rbp-8]
    mov r10, rax
    mov rax, r10
    cmp rax, 3
    setg al
    movzx rax, al
    mov r10, rax
    mov rax, r10
    cmp rax, 0
    jne L_then_5
    jmp L_else_6
L_then_5:
    mov rax, 1
    mov [rbp-16], rax
    jmp L_endif_7
L_else_6:
    mov rax, 0
    mov [rbp-16], rax
    jmp L_endif_7
L_endif_7:
    movsx rax, dword [rbp-8]
    mov r10, rax
    movsx rax, dword [rbp-16]
    mov r11, rax
    mov rax, r10
    mov rdi, rax
    mov rax, r11
    mov rsi, rax
    call add
    mov r10, rax
    mov rax, r10
    mov rsp, rbp
    pop rbp
    ret
