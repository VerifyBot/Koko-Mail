# jsoon - My simple JSON Encoder & Decoder in Python

A simple semi-implementation of the json [RFC](https://www.rfc-editor.org/rfc/rfc8259) for my project


# 🎯 Usage
The following functions are supported:
- `dump(obj, indent=2)`
- `dumps(obj, fp, indent=2)`
- `load(fp)`
- `loads(raw)`

## 🗃️ dump(obj, fp, indent) and dumps(obj, indent)

Serialize Python objects as JSON 

```python
import jsoon

data = {
  "name": "John Doe", "age": 30, "isStudent": False, "balance": 1234.56, "notes": None,
  "address": {"street": "123 Main St", "city": "Anytown", },
  "phoneNumbers": [{"type": "home", "number": "555-1234"},
                   {"type": "work", "number": "555-5678"}],
}

# dump to a file
with open('info.json', 'w') as f:
  jsoon.dump(data, f, indent=2)

# get the raw json
raw = jsoon.dumps(data, indent=2)
```


## 📟 load(fp) and loads(raw)

Deserialize JSON as Python objects 

```python
import jsoon

raw = """
{
  "product_name": "Widget XYZ", "price": 49.99, "is_available": true, "promo": null,
  "description": "This is a high-quality widget that will help you solve any problem.",
  "tags": ["widget", "XYZ", "tool"],
  "reviews": [{"author": "John Smith", "rating": 4, "comment": "Great widget! I use it every day."},
              {"author": "Jane Doe","rating": 5 ,"comment": "This widget is amazing!"}]
}
"""

# load from a file
with open('info.json') as f:
  my_data = jsoon.load(f)

# parse raw json
my_data = jsoon.loads(raw)
```