#include "currencyconverter.h"
#include <QEvent>
#include <QResizeEvent>
#include <QTimer>

bool CurrencyConverter::eventFilter(QObject *obj, QEvent *event)
{
    if (event->type() == QEvent::FocusIn) {
        if (obj == fromInput->getLineEdit() && !fromInput->getText().isEmpty()) {
            fromSuggestions->updateSuggestions(fromInput->getText());
            fromSuggestions->positionUnder(fromInput->getContainer(), centralWidget);
        } else if (obj == toInput->getLineEdit() && !toInput->getText().isEmpty()) {
            toSuggestions->updateSuggestions(toInput->getText());
            toSuggestions->positionUnder(toInput->getContainer(), centralWidget);
        }
    } else if (event->type() == QEvent::FocusOut) {
        if (obj == fromInput->getLineEdit()) {
            QTimer::singleShot(200, this, [this]() {
                if (!fromSuggestions->hasFocus()) {
                    fromSuggestions->setVisible(false);
                    fromSuggestions->setFixedHeight(0);
                }
            });
        } else if (obj == toInput->getLineEdit()) {
            QTimer::singleShot(200, this, [this]() {
                if (!toSuggestions->hasFocus()) {
                    toSuggestions->setVisible(false);
                    toSuggestions->setFixedHeight(0);
                }
            });
        }
    }
    return QMainWindow::eventFilter(obj, event);
}

void CurrencyConverter::resizeEvent(QResizeEvent *event)
{
    QMainWindow::resizeEvent(event);

    if (fromSuggestions->isVisible()) {
        fromSuggestions->positionUnder(fromInput->getContainer(), centralWidget);
    }
    if (toSuggestions->isVisible()) {
        toSuggestions->positionUnder(toInput->getContainer(), centralWidget);
    }
}

void CurrencyConverter::showError(const QString &message)
{
    errorLabel->setText(message);
    errorLabel->setVisible(true);

    QTimer::singleShot(3000, this, [this]() {
        errorLabel->setVisible(false);
    });
}
