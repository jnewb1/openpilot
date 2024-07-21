
def read_table(dat, offset_start):
  row1_start = offset_start
  row2_start = offset_start + 32
  row1 = [int.from_bytes(dat[row1_start+i*2:row1_start+i*2+2], byteorder="big") for i in range(16)]
  row2 = [int.from_bytes(dat[row2_start+i*2:row2_start+i*2+2], byteorder="big") for i in range(16)]

  return row1, row2


candidates = [0x2B690, 0x2b710, 0x2b750]


def strictly_increasing(dat):
  for i in range(len(dat) - 1):
    if dat[i] >= dat[i+1]:
      return False
  return True


with open("data.bin", "rb") as f:
  dat = f.read()

  for i in range(len(dat)):
    row1, row2 = read_table(dat, i)

    if row1[0] != 0 or not strictly_increasing(row1):
      continue

    print(hex(i), row1, row2)
