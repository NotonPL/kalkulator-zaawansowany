# Expression language reference

This is the complete language accepted by the display, the keypad and the CLI. It is implemented by
a real lexer/parser/evaluator (`calc/core`) -- there is no `eval()` anywhere.

## Numbers and operators

| Input | Meaning |
| ----- | ------- |
| `0-9 .` | decimal numbers, scientific notation `1.5e-10`, radix `0x1F`, `0b1010`, `0o17` |
| `+ -` | add / subtract |
| `* /` `× ÷` | multiply / divide |
| `^` or `**` | power (right-associative, `2^-3` allowed) |
| `%` | postfix percent (`50%` = `0.5`) |
| `!` | factorial (`5!`, `fact(0.5)` via Gamma) |
| `( )` | grouping |
| implicit | `2π`, `3(4+1)`, `2sin(30)`, `√16` |

Precedence (low→high): `+ -` → `* /` → unary `±` → `^` → postfix `% !`.

## Constants

`pi π tau τ e phi φ inf c g avogadro boltzmann`

## Functions (also in the in-app *Functions* browser)

| Category | Functions |
| -------- | --------- |
| Trigonometry | `sin cos tan asin acos atan atan2 sinh cosh tanh degrees radians` |
| Logarithms | `log(x[,base]) ln log2 log10 exp` |
| Powers & roots | `sqrt cbrt root(x,n) pow hypot` |
| Rounding & sign | `abs sign floor ceil round(x[,n]) trunc frac` |
| Number theory | `fact gcd lcm mod comb perm` |
| Statistics | `sum min max mean` |

Trig functions respect the active angle unit (`rad`/`deg`/`grad`); inverse trig returns an angle in
that same unit.

## Variables and the previous answer

```
ans          # always holds the last result
```

In the CLI you can define more: `let x = 5`, list them with `vars`.

## Error reporting

Errors are typed and point at the offending character. The GUI shakes the display and shows the
position; the CLI prints a caret:

```
> 1 + )
  ! Expected a number or name but found ')'
      ^
```

## Input repair

When you press `=`, a trailing operator is dropped and missing parentheses are closed, so
`2*(3+4` evaluates to `14` exactly like on a hardware calculator.
