#include "networkmanager.h"
#include <QJsonDocument>
#include <QJsonObject>
#include <QUrl>
#include <QNetworkRequest>

NetworkManager::NetworkManager(QObject *parent)
    : QObject(parent)
{
    manager = new QNetworkAccessManager(this);
    connect(manager, &QNetworkAccessManager::finished,
            this, &NetworkManager::onNetworkReply);
}

void NetworkManager::fetchExchangeRate(const QString &fromCurrency, const QString &toCurrency)
{
    currentToCurrency = toCurrency;

    QString url = QString("https://open.er-api.com/v6/latest/%1").arg(fromCurrency);
    QUrl qurl(url);
    QNetworkRequest request(qurl);
    manager->get(request);
}

void NetworkManager::onNetworkReply(QNetworkReply *reply)
{
    if (reply->error() == QNetworkReply::NoError) {
        QByteArray data = reply->readAll();
        QJsonDocument doc = QJsonDocument::fromJson(data);
        QJsonObject obj = doc.object();

        if (obj.contains("rates")) {
            QJsonObject rates = obj["rates"].toObject();

            if (rates.contains(currentToCurrency)) {
                double rate = rates[currentToCurrency].toDouble();
                emit exchangeRateFetched(rate, currentToCurrency);
            } else {
                emit errorOccurred("Currency not found");
            }
        } else {
            emit errorOccurred("Invalid response from server");
        }
    } else {
        emit errorOccurred("Failed to fetch exchange rate");
    }

    reply->deleteLater();
}
