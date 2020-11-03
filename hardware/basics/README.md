# hardware/basic

## info

> With all those CPU bugs I don't trust software anymore, so I came up 
> with my custom TPM (trademark will be filed soon!). You can't break 
> this, so don't even try.
> 
> [Attachment](https://storage.googleapis.com/gctf-2020-attachments-project/3da8bc17f534eec284ee0f7f0cb473218365fc189dec41931240c2a7dcd0fcea4968cd56561525e184a0043efaff7a5029bb581afbc6ce89491b8384db6d8b1a)
> 
> `basics.2020.ctfcompetition.com 1337`

## writeup

First things first: What is a **TPM**?

> **Trusted Platform Module** (TPM, also known as ISO/IEC 11889) is an international standard for a secure cryptoprocessor, a dedicated microcontroller designed to secure hardware through integrated cryptographic keys.

Seems like some kind of encryption awaits. Let's have a look at what we got:

- main.ccp

- check.sv

A regular C++ program and a **SystemVerilog** file.

> Verilog is used to **design physical logic circuits** but its also serves as a simulation enivonment. It allows you to describe your designs on a very abstract level.
> 
> It's mainly used to:
> 
> - model digital logic circuits
> 
> - simulate and veryify digital logic circuits
> 
> - synthesize digital logic circuits

SystemVerilog is a superset of Verilog and works on a higher abstraction layer. Makes sense, we don't have access to physical hardware thats why it needs to be simulated somehow.

Now that we have a better understanding of what we are dealing with, let's have a look at the code:

```cpp
// main.cpp
#include "obj_dir/Vcheck.h"

#include <iostream>
#include <memory>

int main(int argc, char *argv[]) {
    Verilated::commandArgs(argc, argv);
    std::cout << "Enter password:" << std::endl;
    auto check = std::make_unique<Vcheck>();

    for (int i = 0; i < 100 && !check->open_safe; i++) {
        int c = fgetc(stdin);
        if (c == '\n' || c < 0) break;
        check->data = c & 0x7f;
        check->clk = false;
        check->eval();
        check->clk = true;
        check->eval();
    }
    if (check->open_safe) {
        std::cout << "CTF{real flag would be here}" << std::endl;
    } else {
        std::cout << "=(" << std::endl;
    }
    return 0;
}
```

Right in the first line some custom header file gets referenced which will prevent us from compiling the program. If we search for `Verilated` we'll find that it belongs to a tool called **Verilator** which converts Verilog code into C++/SystemC. Seems like the author used it to compile and import the code from <u>check.sv</u>. We could do the same in order to perform some kind of brute-force attack but lets rather try to understand the code.

The program loops trought the input, character by character, accepting only valid ASCII (0x7f = 127). Looks like toggling `clk` and evaluating the check function simulates a hardware clock. Important is that we get the **flag** when `open_safe` is true.

It's time to dive into the check function:

```verilog
// check.sv
module check(
    input clk,

    input [6:0] data,
    output wire open_safe
);

reg [6:0] memory [7:0];
reg [2:0] idx = 0;

wire [55:0] magic = {
    {memory[0], memory[5]},
    {memory[6], memory[2]},
    {memory[4], memory[3]},
    {memory[7], memory[1]}
};

wire [55:0] kittens = { magic[9:0],  magic[41:22], magic[21:10], magic[55:42] };
assign open_safe = kittens == 56'd3008192072309708;

always_ff @(posedge clk) begin
    memory[idx] <= data;
    idx <= idx + 5;
end

endmodule
```

In order for `open_safe` to be true, `kittens` (a concatenation of 4 `magic` bit chunks) and a specific number need to be equal. 

```verilog
assign open_safe = kittens == 56'd3008192072309708;
```

Verilog operates on bit level so we'll represent the decimal number in binary before we're going to reverse the algorithm.

```
3008192072309708
00001010101011111110111101001011111000101101101111001100
```

> Pay attention to the added 4 most significat bits in order to correctly represent the `56` bits specified.

Lets identify the *magically* extracted bit parts.

```
0000101010  10111111101111010010  111110001011  01101111001100
|---10---|  |------20----------|  |----12----|  |-----14-----|
magic[9:0]  magic[41:22]          magic[21:10]  magic[55:42]
```

Now we know how `magic` needs to look like.

```
magic = { 01101111001100 10111111101111010010 111110001011 0000101010 }
          magic[55:42]   magic[41:22]         magic[21:10] magic[9:0]
```

We also know that `memory` stores our input and consists of 8 elements each 7 bits wide. So if we split `magic` into chunks of 7 bits each, we get the password characters.

```
0110111 1001100 1011111 1101111 0100101 1111000 1011000 0101010
mem[0]  mem[5]  mem[6]  mem[2]  mem[4]  mem[3]  mem[7]  mem[1]
0x37    0x4c    0x5f    0x6f    0x25    0x78    0x58    0x2a
7       L       _       o       %       x       X       *      
```

Their position inside `memory` is defined by the loop variable `idx` which each time increases by 5. It can only hold 3 bits (a decimal 7) which effectively results in a kind of *shuffle*.

A simple python script for reversing could look like this:

```python
char = []
idx = []
memory = ['7', '*', 'o', 'x', '%', 'L', '_', 'X']

i = 0
while len(idx) < 8:
    idx.append(i & 0b111)
    i += 5

print("password: ", end="")

i = 0
while len(char) < 8:
    char.append(memory[idx[i]])
    i += 1

print("".join(char))
# password: 7LoX%*_x
```

If we connect to the challenge server and provide the password we get the flag: `CTF{W4sTh4tASan1tyCh3ck?}`.

### resources

- [Trusted Platform Module – Wikipedia](https://de.wikipedia.org/wiki/Trusted_Platform_Module)

- [Installing - Verilator - Veripool](https://www.veripool.org/projects/verilator/wiki/Installing#_running_verilator)

- [verilator(1) - Linux man page](https://linux.die.net/man/1/verilator)

- [System Verilog Cheatsheet](https://www.cl.cam.ac.uk/teaching/1112/ECAD+Arch/files/SystemVerilogCheatSheet.pdf)

- [Verilog Lecture 1 of 10 - 2009 - YouTube](https://www.youtube.com/watch?v=PybxgAroozA)
