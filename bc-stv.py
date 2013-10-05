# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import math
import json
import sys
import itertools

class Ballot:
    def __init__(self, prefs):
        self.value = 1 # This ballot is worth 1 vote
        self.prefs = prefs # These are the remaining preferences

    def next_choice(self):
        return self.prefs[0]

    def eliminate(self, candidate):
        self.prefs = list(filter(lambda x: x != candidate, self.prefs))

    def is_active(self):
        return len(self.prefs) > 0 and self.value > 0

    @staticmethod
    def from_ranks(obj):
        # Convert a {string -> preference} mapping (from the JSON) into a Ballot
        # If ranks are duplicated/skipped, accept ranks until the first error.
        # XXX This is ugly.
        obj = {k: v for k, v in obj.items() if v != 0} # Filter out 0 ranks.
        if len(obj) == 0: return Ballot([])
        ranks, prefs = zip(*sorted(zip(obj.values(), obj.keys())))
        assert len(ranks) == len(set(ranks)) # XXX Should filter out duplicates
        ranked_prefs = zip(itertools.count(1), ranks, prefs)
        prefs = [pref for i, rank, pref in ranked_prefs if i == rank]
        return Ballot(prefs)

def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        j = json.load(f)
    # Assume j is a list of mappings [{name->pref-value}]
    bc = BC_STV(j)
    bc.bc_stv(7)
    print(bc.elected)

class BC_STV:
    def __init__(self, data):
        self.ballots = list(map(Ballot.from_ranks, data))
        self.elected = []

    def bc_stv(self, seats):
        self.quota = math.floor(len(self.ballots) / (seats + 1)) + 1
        print("Threshold: " + str(self.quota))
        while len(self.elected) < seats:
            self.redistribute()
            mx = max(self.piles.items(), key=lambda kv: value(kv[1]))
            mn = min(self.piles.items(), key=lambda kv: value(kv[1]))
            if value(mx[1]) >= self.quota:
                self.elect(mx[0])
            else:
                self.eliminate(mn[0])

    def redistribute(self):
        active_ballots = [b for b in self.ballots if b.is_active()]
        choice = lambda ballot: ballot.next_choice()
        pls = itertools.groupby(sorted(active_ballots, key=choice), key=choice)
        self.piles = {key: list(values) for key, values in pls}
        print(";  ".join(
            "{}: {}".format(cand, value(l)) for cand,l in self.piles.items()))

    def elect(self, candidate):
        print("Elected: " + candidate)
        self.elected.append(candidate)
        votes = value(self.piles[candidate])
        surplus = votes - self.quota
        transfer = surplus / votes
        for ballot in self.piles[candidate]:
            ballot.value = ballot.value * transfer
        self.eliminate(candidate)

    def eliminate(self, candidate):
        print("Eliminated: " + candidate)
        for lst in self.piles.values():
            for ballot in lst:
                ballot.eliminate(candidate)


def value(ballots):
    return sum(ballot.value for ballot in ballots)

if __name__ == '__main__':
    main()

