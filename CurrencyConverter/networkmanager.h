#ifndef NETWORKMANAGER_H
#define NETWORKMANAGER_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QString>

class NetworkManager : public QObject
{
    Q_OBJECT

public:
    explicit NetworkManager(QObject *parent = nullptr);

    void fetchExchangeRate(const QString &fromCurrency, const QString &toCurrency);

signals:
    void exchangeRateFetched(double rate, const QString &toCurrency);
    void errorOccurred(const QString &errorMessage);

private slots:
    void onNetworkReply(QNetworkReply *reply);

private:
    QNetworkAccessManager *manager;
    QString currentToCurrency;
};

#endif // NETWORKMANAGER_H
