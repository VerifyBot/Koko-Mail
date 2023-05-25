import typing

class JsonEncoder:
  def __init__(self, data, indent=2):
    self.data = data
    self.indent = indent
    self._raw = None

  @property
  def raw(self) -> str:
    """
    Get the raw json
    """
    if self._raw:
      return self._raw

    self._to_raw()
    return self._raw

  def _to_raw(self):
    """
    This method encodes the python objects to raw json and puts it in self._raw.
    """
    self._raw = self.dict_or_list(self.data, lvl=0)

  def __str__(self):
    return f'JsonDecoder(data={str(self.data)[:40]}...)'

  def __repr__(self):
    return f'JsonDecoder(data={str(self.data)[:40]}...)'

  def tabit(self, lvl):
    return ' ' * self.indent * lvl

  def to_any(self, it, lvl):
    if it is None:
      return 'null'
    elif it is True:
      return 'true'
    elif it is False:
      return 'false'
    elif isinstance(it, dict):
      return self.to_object(it, lvl)
    elif isinstance(it, list):
      return self.to_array(it, lvl)
    elif isinstance(it, str):
      return self.to_string(it)
    elif isinstance(it, int):
      return self.to_int(it)
    elif isinstance(it, float):
      return self.to_float(it)

    raise ValueError(f"Object {it} from type {type(it)} cannot be turned into json")

  def to_float(self, n: float) -> str:
    """
    Takes a float as input and returns a json string representing it
    """

    # as much as i want to code it myself,
    # i rather not spend time on precision problems (ie: 123.55 - 123 == 0.5499999999999972)
    return n.__repr__()

  def to_int(self, n: int) -> str:
    """
    Takes an int as input and returns a json string representing it
    """
    if n == 0:
      return ''

    return self.to_int(n // 10) + chr(0x30 + n % 10)

  def to_string(self, s: str) -> str:
    """
    Takes a string as input and returns a json string representing it
    """
    return '"' + s.replace('"', '\\"') + '"'

  def to_array(self, l: list, lvl) -> str:
    """
    Takes a list as input and returns a json string representing it
    """

    a = ""

    for v in l:
      a += self.tabit(lvl + 1) + f'{self.to_any(v, lvl + 1)},\n'

    return "[\n" + a.rstrip(',\n\t') + "\n" + self.tabit(lvl) + "]"

  def to_object(self, d: dict, lvl=0) -> str:
    """
    Takes a dictionary as input and returns a json string representing it
    """

    o = ""

    for i, (k, v) in enumerate(d.items()):
      r = self.to_any(v, lvl + 1)
      o += self.tabit(lvl + 1) + f'"{k}": {r},\n'

    return "{\n" + o.rstrip(',\n\t') + "\n" + self.tabit(lvl) + "}"

  def dict_or_list(self, it, lvl=0):
    if isinstance(it, dict):
      return self.to_object(it, lvl)

    elif isinstance(it, (list, tuple)):
      return self.to_array(it, lvl)


if __name__ == '__main__':
  data = {'mails': [{'id': 1, 'subject': 'a', 'body': 'a', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-06 13:57:02', 'attachments': ''}, {'id': 2, 'subject': 'its me mario!', 'body': 'a super secret message, dont tell anybody...', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-06 14:07:28', 'attachments': ''}, {'id': 3, 'subject': 'third mail a charm', 'body': 'please stop sending me mails\n\ni will block you', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-06 14:08:24', 'attachments': ''}, {'id': 4, 'subject': 'third mail a charm', 'body': 'please stop sending me mails\n\ni will block you', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-06 14:09:45', 'attachments': ''}, {'id': 5, 'subject': 'cool\t', 'body': 'haha\t\nd\n', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-16 18:18:25', 'attachments': ''}, {'id': 6, 'subject': 'cool\tfsdfsdfds', 'body': 'haha\t\nd\n', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-16 18:19:01', 'attachments': ''}, {'id': 7, 'subject': 'fsdf', 'body': 'fdsfsd', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-16 18:28:30', 'attachments': ''}, {'id': 8, 'subject': '21fsdf', 'body': 'f', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-16 18:29:04', 'attachments': ''}, {'id': 9, 'subject': 'ligma lakeket', 'body': 'eheha stock', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-16 18:41:50', 'attachments': ''}, {'id': 10, 'subject': 'stock market', 'body': 'rising!\n', 'sender': 'niryo123', 'recipient': 10, 'timestamp': '2023-04-16 18:42:30', 'attachments': ''}]}


  encoded = JsonEncoder(data)

