"""Strict host-side contract for optional per-instance cave cargo."""
import re


def read_cargo(path):
    lines = path.read_text(encoding='ascii').splitlines()
    if len(lines) < 2 or lines[0] != 'P2_CARGO_1':
        raise ValueError('Invalid cargo header')
    if not re.fullmatch(r'[0-9]+', lines[1]):
        raise ValueError('Invalid cargo count')
    count = int(lines[1])
    if not 1 <= count <= 32 or len(lines) != count + 2:
        raise ValueError('Invalid cargo count')
    result = []
    generators, instances, models = set(), set(), set()
    for line in lines[2:]:
        words = line.split()
        if len(words) != 6:
            raise ValueError('Invalid cargo record')
        generator, instance, model, value, weight, slots = words
        if any(not re.fullmatch(r'[0-9]+', word) for word in (generator,value,weight,slots)):
            raise ValueError('Invalid cargo number')
        generator, value, weight, slots = map(int, (generator, value, weight, slots))
        if (not 0 <= generator <= 0xffffffff or generator in generators or instance in instances or model in models
                or not re.fullmatch(r'[A-Za-z0-9_:/-]{1,90}', instance)
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', model)
                or not 0 <= value <= 1000000 or not 1 <= weight <= 1000 or not 1 <= slots <= 128):
            raise ValueError('Invalid/duplicate cargo identity or parameters')
        generators.add(generator); instances.add(instance); models.add(model)
        result.append(dict(generator=generator, instance=instance, model=model,
                           value=value, weight=weight, slots=slots))
    return result
