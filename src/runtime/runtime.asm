bits 64

section .text

global _start
global exit
global print_int
global print_string
global read_int

extern main

_start:
    call main

    mov rdi, rax
    call exit

exit:
    mov rax, 60
    syscall

print_int:
    push rbp
    mov rbp, rsp
    sub rsp, 32

    mov rax, rdi
    mov rcx, 10
    lea rsi, [rbp-1]
    mov byte [rsi], 0

    cmp rax, 0
    jne .not_zero
    dec rsi
    mov byte [rsi], '0'
    jmp .print

.not_zero:
    xor r8, r8
    cmp rax, 0
    jge .convert
    neg rax
    mov r8, 1

.convert:
    xor rdx, rdx
    div rcx
    add dl, '0'
    dec rsi
    mov [rsi], dl
    test rax, rax
    jnz .convert

    cmp r8, 1
    jne .print
    dec rsi
    mov byte [rsi], '-'

.print:
    lea rdx, [rbp-1]
    sub rdx, rsi

    mov rdi, 1
    mov rax, 1
    syscall

    mov rax, 1
    mov rdi, 1
    push 10
    mov rsi, rsp
    mov rdx, 1
    syscall
    pop rax

    mov rsp, rbp
    pop rbp
    ret

print_string:
    push rdi
    xor rcx, rcx
.len_loop:
    cmp byte [rdi + rcx], 0
    je .done_len
    inc rcx
    jmp .len_loop
.done_len:
    mov rdx, rcx
    pop rsi
    mov rdi, 1
    mov rax, 1
    syscall
    ret

read_int:
    push rbp
    mov rbp, rsp
    sub rsp, 32

    mov rax, 0
    mov rdi, 0
    mov rsi, rsp
    mov rdx, 32
    syscall

    xor rax, rax
    xor rcx, rcx
    mov rsi, rsp
.conv_loop:
    movzx rdx, byte [rsi + rcx]
    cmp dl, 10
    je .done
    cmp dl, 0
    je .done
    sub dl, '0'
    imul rax, 10
    add rax, rdx
    inc rcx
    jmp .conv_loop
.done:
    mov rsp, rbp
    pop rbp
    ret
