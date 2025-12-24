#ifndef CURRENCYCONVERTER_H
#define CURRENCYCONVERTER_H

#include <QMainWindow>
#include <QLineEdit>
#include <QLabel>
#include <QPushButton>
#include "currencydata.h"
#include "networkmanager.h"
#include "suggestionspopup.h"
#include "currencyinput.h"

class CurrencyConverter : public QMainWindow
{
    Q_OBJECT

public:
    CurrencyConverter(QWidget *parent = nullptr);
    ~CurrencyConverter();

protected:
    bool eventFilter(QObject *obj, QEvent *event) override;
    void resizeEvent(QResizeEvent *event) override;

private slots:
    void onFromTextChanged(const QString &text);
    void onToTextChanged(const QString &text);
    void onFromCurrencySelected(const QString &code);
    void onToCurrencySelected(const QString &code);
    void onSwapClicked();
    void onConvertClicked();
    void onClearClicked();
    void onExchangeRateFetched(double rate, const QString &toCurrency);
    void onNetworkError(const QString &error);

private:
    void setupUI();
    void styleApplication();
    void showError(const QString &message);

    QWidget *centralWidget;

    CurrencyInput *fromInput;
    CurrencyInput *toInput;
    QLineEdit *amountInput;

    QLabel *resultLabel;
    QLabel *errorLabel;
    QLabel *updateLabel;

    QPushButton *swapButton;
    QPushButton *convertButton;
    QPushButton *clearButton;

    SuggestionsPopup *fromSuggestions;
    SuggestionsPopup *toSuggestions;

    CurrencyData *currencyData;
    NetworkManager *networkManager;
};

#endif // CURRENCYCONVERTER_H
