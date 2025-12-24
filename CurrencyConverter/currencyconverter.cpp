#include "currencyconverter.h"

CurrencyConverter::CurrencyConverter(QWidget *parent)
    : QMainWindow(parent)
{
    currencyData = new CurrencyData(this);
    networkManager = new NetworkManager(this);

    setupUI();  // interface
    styleApplication(); // styles

    connect(networkManager, &NetworkManager::exchangeRateFetched,
            this, &CurrencyConverter::onExchangeRateFetched);
    connect(networkManager, &NetworkManager::errorOccurred,
            this, &CurrencyConverter::onNetworkError);
}

CurrencyConverter::~CurrencyConverter(){
}
