import argparse
import shlex

from openpilot.selfdrive.debug.auto_fingerprint import auto_fingerprint


FINGERPRINT_COMMAND = "/fingerprint"


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="")
  parser.add_argument("comment", help="Github comment", type=str)
  args = parser.parse_args()
  comment = args.comment

  for line in comment.split("\n"):
    if FINGERPRINT_COMMAND in line:
      start = line.index(FINGERPRINT_COMMAND)
      
      split = shlex.split(line[start:])

      if len(split) not in [2,3]:
        raise Exception(f"Invalid number of arguments: {split}")
    
      if len(split) == 2:
        _, route = split
        platform = None
      if len(split) == 3:
        _, route, platform = split

      auto_fingerprint(route, platform)

      exit(0)
      
  raise Exception(f"{FINGERPRINT_COMMAND} is required to call this job")
  