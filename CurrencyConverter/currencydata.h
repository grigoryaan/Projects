#ifndef CURRENCYDATA_H
#define CURRENCYDATA_H

#include <QObject>
#include <QMap>
#include <QList>
#include <QString>

class CurrencyData : public QObject
{
    Q_OBJECT

public:
    explicit CurrencyData(QObject *parent = nullptr);

    void initialize();

    QString getCurrencyName(const QString &code) const;
    QList<QString> getAllCurrencyCodes() const;
    QString getFlagPath(const QString &code) const;

    bool isValidCurrency(const QString &code) const;

private:
    QMap<QString, QString> currencyNames;
    QList<QString> currencyCodes;
};

#endif // CURRENCYDATA_H
