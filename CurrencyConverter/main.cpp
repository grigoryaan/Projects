#include "currencyconverter.h"
#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    
    CurrencyConverter window;
    window.show();
    
    return app.exec();
}
