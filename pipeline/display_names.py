"""Apply reviewed, source-attested display punctuation without changing identity."""
import copy
from .fragella_trial import normalize
from .model import ROOT, DATA, read, write


def restore_display_names(profiles):
    result = copy.deepcopy(profiles)
    rules = {r['id']: r for r in read(ROOT / 'contracts/display-name-corrections.v1.json')['mappings']}
    for profile in result:
        rule = rules.get(profile['id'])
        if not rule:
            continue
        if (profile['fragranticaId'] != rule['fragranticaId'] or profile['brand'] != rule['brand']
                or profile['name'] not in (rule['previousName'], rule['name'])):
            continue
        # Inherited labels also split contractions (Angel s) or omit terminal
        # apostrophes (Angels). Reviewed rules may repair either representation,
        # but must preserve every identity letter in order.
        if normalize(rule['previousName']).replace(' ', '') != normalize(rule['name']).replace(' ', ''):
            raise ValueError('Display punctuation correction changes identity: ' + profile['id'])
        profile['name'] = rule['name']
        profile['nameAliases'] = sorted(set(profile.get('nameAliases', []) + [rule['previousName']]))
    return result


if __name__ == '__main__':
    from .release import build
    profiles = restore_display_names(read(DATA / 'catalog/profiles.json'))
    build(profiles)
    write(DATA / 'catalog/profiles.json', profiles)
