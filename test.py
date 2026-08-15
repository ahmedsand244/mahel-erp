def compare(mars_value, earth_value):
    if mars_value < earth_value:
        return -1
    if mars_value > earth_value:
        return 1
    return 0


def match_crystals(mars, earth):
    if not mars:
        return []

    if len(mars) == 1:
        return [(mars[0], earth[0])]

    pivot = mars[0]
    earth_less = []
    earth_greater = []
    partner = None

    for item in earth:
        relation = compare(pivot, item)

        if relation < 0:
            earth_greater.append(item)
        elif relation > 0:
            earth_less.append(item)
        else:
            partner = item

    mars_less = []
    mars_greater = []

    for item in mars[1:]:
        relation = compare(item, partner)

        if relation < 0:
            mars_less.append(item)
        elif relation > 0:
            mars_greater.append(item)

    left_pairs = match_crystals(mars_less, earth_less)
    right_pairs = match_crystals(mars_greater, earth_greater)

    return left_pairs + [(pivot, partner)] + right_pairs


def match_crystals_bruteforce(mars, earth):
    pairs = []
    used = [False] * len(earth)

    for m in mars:
        for index, e in enumerate(earth):
            if used[index]:
                continue

            if compare(m, e) == 0:
                pairs.append((m, e))
                used[index] = True
                break

    return sorted(pairs)


if __name__ == "__main__":
    examples = [
        ([45, 10, 80, 25], [25, 80, 45, 10]),
        ([210, 125, 340, 180, 95, 275],
         [95, 340, 275, 210, 125, 180])
    ]

    for mars, earth in examples:
        print("Mars :", mars)
        print("Earth:", earth)
        print("Pairs:", match_crystals(mars, earth))
        print()
