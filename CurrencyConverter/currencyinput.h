#ifndef CURRENCYINPUT_H
#define CURRENCYINPUT_H

#include <QWidget>
#include <QLineEdit>
#include <QLabel>
#include <QString>

class CurrencyInput : public QWidget
{
    Q_OBJECT

public:
    explicit CurrencyInput(const QString &placeholder, const QString &defaultEmoji, QWidget *parent = nullptr);

    QLineEdit* getLineEdit() const;
    QWidget* getContainer() const;

    void setSelectedCurrency(const QString &code, const QString &flagPath);
    void clearInput();
    void resetFlagIfNotMatching();
    QString getText() const;
    QString getSelectedCurrency() const;

signals:
    void textChanged(const QString &text);

private:
    void setupUI(const QString &placeholder, const QString &defaultEmoji);

    QWidget *container;
    QLineEdit *lineEdit;
    QLabel *flagLabel;
    QString selectedCurrency;
    QString defaultEmoji;
};

#endif // CURRENCYINPUT_H
