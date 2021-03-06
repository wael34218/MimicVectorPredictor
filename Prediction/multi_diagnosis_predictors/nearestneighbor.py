import math
import argparse
import gensim
from predictor import Predictor


class NearestNeighbor(Predictor):

    def __init__(self, filename, decay=0, k=3, f=5, window=600, size=600):
        self._filename = filename
        self._decay = decay
        self._k = k
        self._f = f
        self._window = window
        self._size = size
        self._props = {"k": k, "f": f, "window": window, "size": size, "decay": decay}
        super(NearestNeighbor, self).__init__(filename)

    def train(self, filename):
        self._nn_mat = []
        self._prediction = []
        self._prediction_lists = []
        self._filename = filename
        self._events_mask = {}

        with open(filename) as f:
            sentences = [s[:-1].replace(",", "").split(' ') for s in f.readlines()]
            self._model = gensim.models.Word2Vec(sentences, sg=0, window=self._window,
                                                 size=self._size, min_count=1, workers=20)

        for diag in self._diags:
            self._events_mask[diag] = [0] * len(self._uniq_events)
            for e, d in self._model.most_similar(diag, topn=self._f):
                self._events_mask[diag][self._events_index.index(e)] = 1

        with open(filename) as f:
            for line in f:
                feed_index = line[0:line.rfind(" d_")].rfind(",")
                feed_events = line[0:feed_index].replace(",", "").split(" ")
                last_admission = line[feed_index:].replace("\n", "").replace(",", "").split(" ")
                actual = set([x for x in last_admission if x.startswith('d_')])

                seq_array = [0] * len(self._uniq_events)
                te = len(feed_events)
                for i, e in enumerate(feed_events):
                    seq_array[self._events_index.index(e)] += math.exp(self._decay*(i-te+1)/te)
                self._nn_mat.append(seq_array)

                result = [0] * len(self._diags)
                for diag in actual:
                    result[self._diags.index(diag)] = 1
                self._prediction.append(result)
                self._prediction_lists.append(actual)

    def predict(self, pred_seq):
        prediction = set()
        for diag in self._diags:
            dist = []
            for seq in self._nn_mat:
                dist.append(sum([m*(x-y)**2 for x, y, m in
                                 zip(seq, pred_seq, self._events_mask[diag])]))

            min_values = sorted(dist)
            count = 0
            for i in range(self._k):
                count += diag in self._prediction_lists[dist.index(min_values[i])]

            if count > self._k / 2.0:
                prediction.add(diag)

        return prediction

    def test(self, filename):
        with open(filename) as f:
            for line in f:
                feed_index = line[0:line.rfind(" d_")].rfind(",")
                feed_events = line[0:feed_index].replace(",", "").split(" ")
                last_admission = line[feed_index:].replace("\n", "").replace(",", "").split(" ")
                actual = set([x for x in last_admission if x.startswith('d_')])

                seq_array = [0] * len(self._uniq_events)
                te = len(feed_events)
                for i, e in enumerate(feed_events):
                    seq_array[self._events_index.index(e)] += math.exp(self._decay*(i-te+1)/te)

                prediction = self.predict(seq_array)
                print(prediction)
                print(actual)
                print("==========")
                self.stat_prediction(prediction, actual)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CBOW Similarity')
    parser.add_argument('-w', '--window', action="store", default=10, type=int,
                        help='Set max skip length between words (default: 10)')
    parser.add_argument('-s', '--size', action="store", default=600, type=int,
                        help='Set size of word vectors (default: 600)')
    parser.add_argument('-d', '--decay', action="store", default=5, type=float,
                        help='Set exponential decay through time (default: 5)')
    parser.add_argument('-f', '--features', action="store", default=5, type=int,
                        help='Set number of significant features (default: 5)')
    parser.add_argument('-k', '--k', action="store", default=5, type=int,
                        help='Set number of nearest neighbors (default: 3)')
    args = parser.parse_args()

    model = NearestNeighbor('../../Data/w2v/mimic_train_me_0', decay=args.decay, k=args.k,
                            f=args.features, window=args.window, size=args.size)
    train_files = []
    test_files = []
    for i in range(1):
        train_files.append('../../Data/w2v/mimic_train_me_'+str(i))
        test_files.append('../../Data/w2v/mimic_test_me_'+str(i))

    model.cross_validate(train_files, test_files)
    model.report_accuracy()
    model.write_stats()
    print(model.accuracy)
