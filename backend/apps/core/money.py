from decimal import Decimal


def indian_format(value) -> str:
    """1234567.5 → "12,34,567.50" (Indian digit grouping), keeping the sign."""
    number = Decimal(str(value))
    sign = "-" if number < 0 else ""
    whole, fraction = f"{abs(number):.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return sign + ",".join([*groups, tail]) + "." + fraction
