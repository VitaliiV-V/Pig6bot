import json
from collections import defaultdict
from math import log
import random

with open("assets/dataset.json", "r", encoding="utf-8") as f:
    data = json.load(f)


class MarkovChain:

    def __init__(self, n, dataset):
        self.prob = defaultdict(lambda: defaultdict(int))
        self.gen = defaultdict(list)
        self.cnt = defaultdict(int)
        self.smooth = set()
        self.ln = n
        for message in dataset["messages"]:
            for ch in ".,!?()":
                message = message.replace(ch, "")
            message = message.lower()
            message = "% " * self.ln + message + " $"
            tokens = message.split()
            for i in range(len(tokens) - self.ln):
                context = tuple(tokens[i : i + self.ln])
                word = tokens[i + self.ln]
                self.prob[context][word] += 1
                self.cnt[context] += 1
                self.smooth.add(word)

        alpha = 0.05
        V = len(self.smooth)

        for context, val in self.prob.items():
            total = sum(val.values())

            words = []
            probs = []

            for word, count in val.items():
                words.append(word)
                probs.append(count / total)

            self.gen[context] = (words, probs)

    def text(self, minln, maxln, a, b, temp):
        ln = random.randint(minln, maxln)
        s = ""
        text = ["%"] * self.ln
        for i in range(ln):
            if temp - b * a**i >= 2:
                temp = int(temp - b * a**i)
            context = []
            for j in range(self.ln):
                context.append(text[-(j + 1)])
            context.reverse()
            context = tuple(context)
            xx = len(self.gen[context])
            if len(self.gen[context]) == 0:
                for j in range(self.ln):
                    text.append("%")

                context = []
                for j in range(self.ln):
                    context.append(text[-(j + 1)])
                context.reverse()
                context = tuple(context)

            words, probs = self.gen[context]
            cur = random.choices(words, weights=probs)[0]
            if cur == "$":
                break
            s += f"{cur} "
            text.append(cur)
        s = s[0].upper() + s[1:]
        return s


class Generator:

    def __init__(self, _a=0.9, _b=7, _temp=100):
        self.a = _a
        self.b = _b
        self.temp = _temp

        self.chain1 = MarkovChain(1, data)

        self.chain2 = MarkovChain(2, data)

    def gen(self, minln, maxln):
        if random.randint(0, 1):
            s = self.chain1.text(minln, maxln, self.a, self.b, self.temp)
        else:
            s = self.chain2.text(minln, maxln, self.a, self.b, self.temp)
        return s

    def train(self, s):
        with open("assets/dataset.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        data["messages"].append(s)

        with open("assets/dataset.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        self.chain1 = MarkovChain(1, data)

        self.chain2 = MarkovChain(2, data)
