import _io
import typing

from jsoon.decoder import JsonDecoder
from jsoon.encoder import JsonEncoder

class JSONError(Exception):
  pass


def loads(raw: str) -> typing.Union[dict, list]:
  """Take a json string and parse it into a python object"""
  try:
    return JsonDecoder(raw).data
  except Exception as e:
    raise JSONError(f'Failed to parse json: {e}') from e

def load(fp: typing.Union[_io.TextIOWrapper, str]):
  """Take a json file and parse it into a python object"""
  if isinstance(fp, str):
    with open(fp, encoding='utf-8') as f:
      raw = f.read()
  else:
    raw = fp.read()

  return loads(raw)


def dumps(obj: typing.Union[dict, list, tuple], indent: int = 2) -> str:
  """Take a python object and return its json raw format"""
  try:
    return JsonEncoder(obj, indent).raw
  except Exception as e:
    raise JSONError(f'Failed to dump json: {e}') from e

def dump(obj: typing.Union[dict, list, tuple], fp: typing.Union[_io.TextIOWrapper, str], indent: int = 2):
  """Take a python object and dump it into a json file"""
  js = dumps(obj, indent)

  if isinstance(fp, str):
    with open(fp, 'w', encoding='utf-8') as f:
      f.write(js)
  else:
    fp.write(js)


if __name__ == '__main__':
  print(dumps({"size": 5}, indent=0))