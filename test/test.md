# Test document

## This is a title

Text with paragraphs.
Each seperated by an empty line.

*Italics* and **bold**.
Also `monospace`.
UTF8 should work: äüÖß Ø αβγ ∀ 😊! This is: ¡great!

This is a [web link](http://example.org/). Also documents can link to [other documents](other/document).

## Advanced formatting

* This is
* a simple
* list

And also

* This

* is a

    * sublist

    * text

* list
with

    paragrphs in items

1. numbered
2. list

TeX formulas: $X \in M$.

$$ \sum_{i=1}^5 X_i \lambda^i $$

Image: ![](test1.png) ![](test2.png). Non-Markdown files are served normally by the server!

## Preformatted blocks / code blocks

Without syntax highlighting:

```
--+-> Some text which
  |
  +--> is preformatted
```

With highlighting:

```python
def fib(x):
    if x == 0 or x == 1: return 0
    return fib(x-1) + fib(x-2)

print(fib(5))
```

With many different languages:

```sql
select *
from table
where a < b
```
