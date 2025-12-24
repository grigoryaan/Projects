#include "currencyconverter.h"
#include <QTimer>

void CurrencyConverter::onFromTextChanged(const QString &text)
{
    fromInput->resetFlagIfNotMatching();

    if (text.isEmpty()) {
        fromSuggestions->setVisible(false);
        fromSuggestions->setFixedHeight(0);
        return;
    }

    fromSuggestions->updateSuggestions(text);
    fromSuggestions->positionUnder(fromInput->getContainer(), centralWidget);
}

void CurrencyConverter::onToTextChanged(const QString &text)
{

    toInput->resetFlagIfNotMatching();

    if (text.isEmpty()) {
        toSuggestions->setVisible(false);
        toSuggestions->setFixedHeight(0);
        return;
    }

    toSuggestions->updateSuggestions(text);
    toSuggestions->positionUnder(toInput->getContainer(), centralWidget);
}

void CurrencyConverter::onFromCurrencySelected(const QString &code)
{
    QString flagPath = currencyData->getFlagPath(code);
    fromInput->setSelectedCurrency(code, flagPath);
}

void CurrencyConverter::onToCurrencySelected(const QString &code)
{
    QString flagPath = currencyData->getFlagPath(code);
    toInput->setSelectedCurrency(code, flagPath);
}

void CurrencyConverter::onSwapClicked()
{
    if (fromInput->getSelectedCurrency().isEmpty() && toInput->getSelectedCurrency().isEmpty()) {
        return;
    }

    QString tempCode = fromInput->getSelectedCurrency();
    QString tempText = fromInput->getText();
    QString tempFlagPath = currencyData->getFlagPath(tempCode);

    QString fromCode = toInput->getSelectedCurrency();
    QString fromFlagPath = currencyData->getFlagPath(fromCode);
    fromInput->setSelectedCurrency(fromCode, fromFlagPath);

    toInput->setSelectedCurrency(tempCode, tempFlagPath);

    fromSuggestions->setVisible(false);
    fromSuggestions->setFixedHeight(0);
    toSuggestions->setVisible(false);
    toSuggestions->setFixedHeight(0);
}

void CurrencyConverter::onConvertClicked()
{
    errorLabel->setVisible(false);

    QString fromCurrency = fromInput->getSelectedCurrency();
    QString toCurrency = toInput->getSelectedCurrency();

    if (fromCurrency.isEmpty() || toCurrency.isEmpty()) {
        showError("Please select both currencies from the list");
        return;
    }

    if (fromInput->getText().toUpper() != fromCurrency || toInput->getText().toUpper() != toCurrency) {
        showError("Please select currencies from the suggestion list");
        return;
    }

    bool ok;
    double amount = amountInput->text().toDouble(&ok);

    if (!ok || amount <= 0) {
        showError("Please enter a valid amount");
        return;
    }

    networkManager->fetchExchangeRate(fromCurrency, toCurrency);
}

void CurrencyConverter::onClearClicked()
{
    fromInput->clearInput();
    toInput->clearInput();
    amountInput->clear();

    resultLabel->setVisible(false);
    errorLabel->setVisible(false);
    fromSuggestions->setVisible(false);
    fromSuggestions->setFixedHeight(0);
    toSuggestions->setVisible(false);
    toSuggestions->setFixedHeight(0);
}

void CurrencyConverter::onExchangeRateFetched(double rate, const QString &toCurrency)
{
    bool ok;
    double amount = amountInput->text().toDouble(&ok);

    if (ok && amount > 0) {
        double result = amount * rate;
        resultLabel->setText(QString::number(result, 'f', 2) + " " + toCurrency);
        resultLabel->setVisible(true);
    }
}

void CurrencyConverter::onNetworkError(const QString &error)
{
    showError(error);
}
