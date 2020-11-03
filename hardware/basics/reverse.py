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
