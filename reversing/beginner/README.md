# reversing/beginner

## info

> Dust off the cobwebs, let's reverse!
> 
> [Attachment](https://storage.googleapis.com/gctf-2020-attachments-project/f0c3f1cbf2b64f69f07995ebf34aa10aed3299038b4a006b2776c9c14b0c762024bc5056b977d9161e033f80ff4517556d79af101088b651b397a27d4a89f2a1)

## writeup

Using `file` on the attachment reveals a *little-endian* binary.

```shell
ELF 64-bit LSB shared object, x86-64
```

Running it shows a prompt asking us to input the **Flag**.

```shell
Flag: AAAAAAAAAAAAAAAA
FAILURE
```

If we run the binary with `ltrace` we see that at some point a string compare takes place. Now we already know that our flag needs to be **15 characters** long. (Excluding null-character)

```c
strncmp("AAAAAAAAAAAAAAA", "FX[Vc\005|x\2540\200`L3]\002\020\005\357\333\377\177", 16)
```

Let's disassemble the binary with `objdump -M intel -d ./binary` and look for the main function. It seems like some obscurification happens before `strncmp`.

```nasm
10be:   pshufb  xmm0,XMMWORD PTR [rip+0x2fa9]    # 4070 <SHUFFLE>
10c7:   paddd   xmm0,XMMWORD PTR [rip+0x2f91]    # 4060 <ADD32>
10cf:   pxor    xmm0,XMMWORD PTR [rip+0x2f79]    # 4050 <XOR>
10d7:   movaps  XMMWORD PTR [rsp+0x10],xmm0
10dc:   call    1030 <strncmp@plt>
10e1:   test    eax,eax
10e3:   jne     1100 <main+0x80>
```

First **shuffle** the input based on a byte mask, then **add** some bytes and finally **xor** the result with another byte mask.

We can find the byte masks in the *.data* section using `objdump -s ./binary`.

```
Inhalt von Abschnitt .data:
4040 00000000 00000000 48400000 00000000  ........H@......
4050 7658b449 8d1a5f38 d423f834 eb86f9aa  vX.I.._8.#.4....
4060 efbeadde addee1fe 37133713 66746367  ........7.7.ftcg
4070 02060701 050b090e 030f0408 0a0c0d00  ................
4080 20200000 00000000                      ......
```

After all this manipulation the output string gets compared with the input string and if `strncmp` returned 0, which means the strings were equal, `test` will set the **ZF** and `jne` does not jump. Flow continues and we arrive at another `strncmp`. 

```nasm
10e5:   mov    rsi,QWORD PTR [rip+0x2f94]    # 4080 <EXPECTED_PREFIX>
10ec:   mov    edx,0x4
10f1:   mov    rdi,rbp
10f4:   call   1030 <strncmp@plt>
```

This time checking if the first 4 characters match a specific prefix, which we find after
following the address stored at `4080`.

    Inhalt von Abschnitt .rodata:
    2000 01000200 466c6167 3a200025 31357300  ....Flag: .%15s.
    2010 53554343 45535300 4641494c 55524500  SUCCESS.FAILURE.
    2020 4354467b 00                          CTF{.

If we run `ltrace` again and use our new knowledge to provide a more specific input we notice that the manipulated string looks not so random anymore.

```c
strncmp("CTF{AAAAAAAAAA}", "CX[{c\005|Df0\200`L3]", 16)
```

### solution

Because the input and output strings must be equal we can abuse the fact that they get **shuffled** along the way and reason about characters at different indices. This works for both directions, either by applying the algorithm regular (top-down) or in reverse.

```
input      C  T  F  {                                } \0

index      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
shuffle    2  6  7  1  5  b  9  e  3  f  4  8  a  c  d  0
add       ef be ad de ad de e1 fe 37 13 37 13 66 74 63 67
xor       76 58 b4 49 8d 1a 5f 38 d4 23 f8 34 eb 86 f9 aa

charcode  43 54 46 7b             
output     C  T  F  {                                } \0
```

For example, the `F` in the input string gets shuffled to position 0 and after adding and xoring should result in `C`.

```python
# input[shuffle[0]] + add[0] ^ xor[0]
0x46 + 0xef ^ 0x76 = 0x143 # Ń
```

#### carry bits

What happend? We excpected `C` but got `Ń`. If we read about the [paddd](https://www.felixcloutier.com/x86/paddb:paddw:paddd:paddq) instruction we see that it adds in 4 Byte chunks and discards any carry on the highest byte addition.

> The PADDD and VPADDD instructions add packed **doubleword integers** from 
> the first source operand and second source operand and store the packed 
> integer results in the destination operand. When an individual result is too large to be represented in 32 bits (overflow), the result is wrapped around and the low 32 bits are written to the destination operand (that is, the carry is ignored).

This means we are dealing with carry bits and need to add them to the following addition if we encounter some.

```python
if (0x46 + 0xef > 0xff):
    # carry bit for the next addition
(0x46 + 0xef) & 0xff ^ 0x76 = 0x43 # C
```

If we now continue and try to reconstruct the character at index 6 by applying the algorithm in reverse we need to remember this carry.

```python
# add[1] + carry ^ xor[1] = output[1]
x + (0xbe + 0x1) ^ 0x58 = 0x54 # T
x = (0x58 ^ 0x54) - (0xbe + 0x1)
x = 0xc - 0xbf 
    # result < 0, we need to carry 1 bit again
x = 0x10c - 0xbf
x = 0x4d # M
```

```
input      C   T   F  {       [M]                      } \0  

index      0   1   2  3  4  5 [6] 7  8  9  a  b  c  d  e  f
shuffle    2  [6]  7  1  5  b  9  e  3  f  4  8  a  c  d  0
add       ef [be] ad de ad de e1 fe 37 13 37 13 66 74 63 67
xor       76 [58] b4 49 8d 1a 5f 38 d4 23 f8 34 eb 86 f9 aa

expected  43 [54] 46 7b      [4d]
output     C  [T]  F  {       [M]                      } \0
```

Let's do it once more but this time from the other direction, top-down: The `{` from our input gets shuffled to index `8` before adding and xoring with the masks.

```python
# input[3] + add[8] ^ xor[8]
0x7b + 0x37 ^ 0xd4 = 0x66 # f
```

    input      C  T  F [{]             [f]                 } \0
    
    index      0  1  2 [3] 4  5  6  7   8   9  a  b  c  d  e  f
    shuffle    2  6  7  1  5  b  9  e  [3]  f  4  8  a  c  d  0
    add       ef be ad de ad de e1 fe [37] 13 37 13 66 74 63 67
    xor       76 58 b4 49 8d 1a 5f 38 [d4] 23 f8 34 eb 86 f9 aa
    
    expected  43 54 46 7b             [66]
    output     C  T  F  {              [f]                 } \0

If we continue doing this and pay close attention for any possible **carry bits** we'll soon complete the flag: `CTF{S1MDf0rM3!}`.
