if __name__ == '__main__':
    from pprint import pprint

    from numpy.random import permutation
    from sklearn import svm, datasets
    from watchdog_man.watcher import Watcher

    w = Watcher()

    @w.log(name='test')
    def test(a, b, c):
        print('a * b ' + str(a * b))
        with open('test.txt', 'w') as f:
            f.write('a b c ' + str(c))
        return a - b

    @w.log(name='test_redirect_files', redirect_files=True)
    def test2(a, b, c):
        print('a * b ' + str(a * b))
        with open('test.txt', 'w') as f:
            f.write('a b c ' + str(c))
        return a - b

    @w.log(name='main')
    def main(C, gamma):
        iris = datasets.load_iris()
        perm = permutation(iris.target.size)
        iris.data = iris.data[perm]
        iris.target = iris.target[perm]
        clf = svm.SVC(C, 'rbf', gamma=gamma)
        clf.fit(iris.data[:90],
                iris.target[:90])
        print(clf.score(iris.data[90:],
                        iris.target[90:]))

    test(10, b=30, c=10)
    test2(10, b=30, c=10)
    main(C=1.0, gamma=0.7)
    pprint(w.logs)
