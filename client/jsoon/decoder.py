import enum
import pprint
import typing


class JsonDecoder:
  RawJson: str = typing.T

  def __init__(self, raw: str):
    self.raw = raw
    self._decoded = None

  @property
  def data(self) -> typing.Union[list, dict]:
    """
    Get the decoded json as dict.
    """
    if self._decoded:
      return self._decoded

    self._decode()
    return self._decoded

  def _decode(self):
    """
    This method decodes the raw json and puts it in self._decoded.
    """
    self._decoded = JsonDecoder.consume_object_or_array(self.raw)[0]

  def __str__(self):
    return f'JsonDecoder(data={str(self.data)[:40]}...)'

  def __repr__(self):
    return f'JsonDecoder(data={str(self.data)[:40]}...)'

  @staticmethod
  def consume_string(s) -> typing.Tuple[str, RawJson]:
    """
    Get raw json part with the string at the beginning,
    and return the string it finds and the rest of the raw json.
    """

    s = s.strip()

    if s[0] != '"':
      raise ValueError(f'Expected string identifier ", got {s[0]}')

    if s.startswith('""'):
      return "", s[2:].strip()


    i = 1
    val = ""

    # basically stop when " is seen but not \"
    while not (len(val) >= 1 and s[i] == '"' and s[i - 1] != '\\'):
      val += s[i]
      i += 1

    return val, s[i + 1:].strip()

  """
  # Notes:
  - when you consume objects and arrays, skip the initial identifier ({ or [)
  - when you consume strings, keep the identifier (")
  
  # ITZNOTBUGITZAFEATURE
  - you can end arrays and objects with , like python allows you ([1,2,])
    so even though its not following the RFC its still better :>
  """

  @staticmethod
  def consume_number(s):
    """
    Valid inputs:

    normal: 100, 150, -200
    decimal: 15.67, -12.1, 99.999
    exponent: 3e-3 , 6E+10, 2e4, 1.1e-
    """
    s = s.strip()


    if s[0] == '-':
      i = 1
      is_negative = True
    else:
      i = 0
      is_negative = False

    num = 0

    is_decimal = False
    decimal_count = 1

    while s[i] not in ',]}eE':
      if s[i] == '.':
        assert not is_decimal, "Invalid number, found multiple decimal identifiers"
        is_decimal = True
        i += 1
        continue

      if s[i] in '0123456789':
        if not is_decimal:
          num = (num * 10) + (ord(s[i]) - 0x30)
        else:
          num = num + (ord(s[i]) - 0x30) / pow(10, decimal_count)
          decimal_count += 1
      else:
        break

      i += 1

    if s[i].lower() == 'e':
      i += 1

      is_expo_negative = False

      if s[i] in '-+':
        is_expo_negative = s[i] == '-'
        i += 1

      expo_num = 0

      was_whiled = False

      while s[i] in '0123456789':
        was_whiled = True
        expo_num = (expo_num * 10) + (ord(s[i]) - 0x30)
        i += 1

      assert was_whiled, "Missing value after exponential symbol e"

      num = num * pow(10, -expo_num if is_expo_negative else expo_num)

    return -num if is_negative else num, s[i:].strip()

  @staticmethod
  def consume_array(s, a):
    s = s.strip()

    if s[0] == ']':
      return a, s[1:].strip()

    item, s = JsonDecoder.consume_any(s)

    a.append(item)

    # expect , for next or ] for exit
    if s[0] == ',':
      return JsonDecoder.consume_array(s[1:], a)
    elif s[0] == ']':
      return JsonDecoder.consume_array(s, a)

    raise ValueError(f"Expected either a new array item or an array close identifier, got {s[0]}")

  @staticmethod
  def consume_any(s):
    s = s.strip()

    if s[0] == '{':
      return JsonDecoder.consume_object(s[1:], {})
    elif s[0] == '[':
      return JsonDecoder.consume_array(s[1:], [])
    elif s[0] == '"':
      return JsonDecoder.consume_string(s)
    elif s.startswith('true'):
      return True, s[4:].strip()
    elif s.startswith('false'):
      return False, s[5:].strip()
    elif s.startswith('null'):
      return None, s[4:].strip()

    return JsonDecoder.consume_number(s)

  @staticmethod
  def consume_object(s, d):
    s = s.strip()

    if s[0] == '}':
      return d, s[1:].strip()

    # expecting object key (string)
    key, s = JsonDecoder.consume_string(s)

    if s[0] != ":":
      raise ValueError(f"Expected delimiter identified :, got {s[0]}")

    value, s = JsonDecoder.consume_any(s[1:])


    d[key] = value

    # expect , for next or } for exit
    if s[0] == ',':
      return JsonDecoder.consume_object(s[1:], d)
    elif s[0] == '}':
      return JsonDecoder.consume_object(s, d)

    raise ValueError(f"Expected either a new key value pair or an object close identifier, got {s[0]}")

  @staticmethod
  def consume_object_or_array(s):
    s = s.strip()

    if s[0] == '{':
      return JsonDecoder.consume_object(s[1:], {})
    elif s[0] == '[':
      return JsonDecoder.consume_array(s[1:], [])
    else:
      raise ValueError('Expected object or array')


if __name__ == '__main__':
  raw = """
{
  "error_code": "02",
  "error": ""
}
  """

  # Issue detected: 1 char strings are broken

  decoder = JsonDecoder(raw)
  print(decoder.data)
