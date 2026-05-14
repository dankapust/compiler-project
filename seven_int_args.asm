bits 64

section .text
extern print_int
extern print_string
extern read_int
extern exit

global sum7
sum7:
    push rbp
    mov rbp, rsp
    sub rsp, 160
    mov [rbp-8], rdi
    mov [rbp-16], rsi
    mov [rbp-24], rdx
    mov [rbp-32], rcx
    mov [rbp-40], r8
    mov [rbp-48], r9
entry_sum7_1:
    mov rax, [rbp-8]
    mov [rbp-56], rax
    mov rax, [rbp-16]
    mov [rbp-64], rax
    mov rax, [rbp-24]
    mov [rbp-72], rax
    mov rax, [rbp-32]
    mov [rbp-80], rax
    mov rax, [rbp-40]
    mov [rbp-88], rax
    mov rax, [rbp-48]
    mov [rbp-96], rax
    mov rax, [rbp+16]
    mov [rbp-104], rax
    movsx rax, dword [rbp-56]
    mov [rbp-16], rax
    movsx rax, dword [rbp-64]
    mov [rbp-24], rax
    mov rax, [rbp-16]
    add rax, [rbp-24]
    mov [rbp-32], rax
    movsx rax, dword [rbp-72]
    mov [rbp-40], rax
    mov rax, [rbp-32]
    add rax, [rbp-40]
    mov [rbp-48], rax
    movsx rax, dword [rbp-80]
    mov [rbp+16], rax
    mov rax, [rbp-48]
    add rax, [rbp+16]
    mov r10, rax
    movsx rax, dword [rbp-88]
    mov r11, rax
    mov rax, r10
    add rax, r11
    mov r10, rax
    movsx rax, dword [rbp-96]
    mov r11, rax
    mov rax, r10
    add rax, r11
    mov r10, rax
    movsx rax, dword [rbp-104]
    mov r11, rax
    mov rax, r10
    add rax, r11
    mov r10, rax
    mov rax, r10
    mov rsp, rbp
    pop rbp
    ret
    jmp exit_sum7_2
exit_sum7_2:

global main
main:
    push rbp
    mov rbp, rsp
    sub rsp, 16
entry_main_3:
    mov rax, 1
    mov rdi, rax
    mov rax, 2
    mov rsi, rax
    mov rax, 3
    mov rdx, rax
    mov rax, 4
    mov rcx, rax
    mov rax, 5
    mov r8, rax
    mov rax, 6
    mov r9, rax
    mov rax, 7
    sub rsp, 8
    mov qword [rsp], rax
    sub rsp, 8
    call sum7
    add rsp, 16
    mov r10, rax
    mov rax, r10
    mov rsp, rbp
    pop rbp
    ret
    jmp exit_main_4
exit_main_4:
