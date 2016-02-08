import argparse
from binarypredictor import BinaryPredictor
from skipgram import SkipGram
from cbowsim import CbowSim
from collaborative import CollaborativeFiltering


class Ensemble(BinaryPredictor):
    def __init__(self, filename, window=10, size=600, decay=5, stopwords=0, threshold=0.5):
        self._window = window
        self._size = size
        self._decay = decay
        self._stopwords = stopwords
        self._threshold = threshold
        self._stopwordslist = []
        self._props = {"window": window, "size": size, "decay": decay, "stopwords": stopwords,
                       "threshold": threshold}
        super(Ensemble, self).__init__(filename)

        self.collaborative = CollaborativeFiltering(filename, window, size, decay, stopwords)
        self.skipgram = SkipGram(filename, window, size, decay, stopwords)
        self.cbowsim = CbowSim(filename, window, size, decay, stopwords)

    def train(self, filename):
        self.collaborative.train(filename)
        self.cbowsim.train(filename)
        self.skipgram.train(filename)
        self._prior = self.cbowsim._prior

    def predict(self, feed_events):
        cf_preds = self.collaborative.predict(feed_events)
        cbow_preds = self.cbowsim.predict(feed_events)
        skip_preds = self.skipgram.predict(feed_events)
        predictions = {}
        for diag in self._diags:
            predictions[diag] = cf_preds[diag] * cbow_preds[diag] * skip_preds[diag]
        return predictions

    def test(self, filename):
        with open(filename) as f:
            lines = f.readlines()
            for line in lines:
                feed_events = line.split("|")[2].split(" ")
                feed_events = [w for w in feed_events if w not in self._stopwordslist]
                actual = line.split("|")[0].split(",")
                predictions = self.predict(feed_events)
                for diag in self._diags:
                    self.stat_prediction(predictions[diag], (diag in actual), diag,
                                         (diag in feed_events))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SkipGram Similarity')
    parser.add_argument('-w', '--window', action="store", default=10, type=int,
                        help='Set max skip length between words (default: 10)')
    parser.add_argument('-s', '--size', action="store", default=600, type=int,
                        help='Set size of word vectors (default: 600)')
    parser.add_argument('-d', '--decay', action="store", default=5, type=float,
                        help='Set exponential decay through time (default: 5)')
    parser.add_argument('-sw', '--stopwords', action="store", default=0, type=int,
                        help='Set number of stop words (default: 0)')
    parser.add_argument('-t', '--threshold', action="store", default=0.2, type=float,
                        help='Threshold for prediction probability (default: 0.2)')
    args = parser.parse_args()

    train_files = []
    test_files = []
    model = Ensemble('../Data/seq_combined/mimic_train_0',
                     args.window, args.size, args.decay, args.stopwords, args.threshold)

    for i in range(10):
        train_files.append('../Data/seq_combined/mimic_train_'+str(i))
        test_files.append('../Data/seq_combined/mimic_test_'+str(i))

    model.cross_validate(train_files, test_files)
    model.report_accuracy()
    model.write_stats()
    print(model.accuracy)