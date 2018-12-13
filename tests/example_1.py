if __name__ == '__main__':
    from pprint import pprint

    from numpy.random import permutation
    from sklearn import svm, datasets
    from watchdog_man.watcher import Watcher

    # create a telegram bot and paste its token to telegram_token.txt
    try:
        token = open('telegram_token.txt').read().strip()
    except:
        token = None

    # to find out your chat id, add your bot and send it a message.
    # then, visit https://api.telegram.org/bot<BOTTOKEN>/getUpdates
    # and copy/paste the id
    try:
        chat_id = open('chat_id.txt').read().strip()
    except:
        chat_id = None

    w = Watcher(telegram_token=token)

    @w.log(name='test', collect_print=True, collect_files=True)
    def test(a, b, c):
        print('a * b ' + str(a * b))
        with open('test.txt', 'w') as f:
            f.write('a b c ' + str(c))
        return a - b

    @w.log(name='test2', collect_print=True)
    @w.notify_via_telegram(name='test2', chat_id=chat_id)
    def test2(a, b, c):
        print('a * b ' + str(a * b))
        with open('test.txt', 'w') as f:
            f.write('a b c ' + str(c))
        return a - b

    @w.log(name='main', collect_print=True)
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
    test(10, b=30, c=10)
    test2(10, b=30, c=10)
    main(C=1.0, gamma=0.7)
    pprint(w.logs)
