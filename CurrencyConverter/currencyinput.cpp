#include "currencyinput.h"
#include <QHBoxLayout>
#include <QPixmap>

CurrencyInput::CurrencyInput(const QString &placeholder, const QString &defaultEmoji, QWidget *parent)
    : QWidget(parent), defaultEmoji(defaultEmoji)
{
    setupUI(placeholder, defaultEmoji);
}

void CurrencyInput::setupUI(const QString &placeholder, const QString &emoji)
{
    container = new QWidget(this);
    container->setObjectName("inputContainer");
    container->setFixedHeight(45);

    QHBoxLayout *mainLayout = new QHBoxLayout(this);
    mainLayout->setContentsMargins(0, 0, 0, 0);
    mainLayout->addWidget(container);

    QHBoxLayout *containerLayout = new QHBoxLayout(container);
    containerLayout->setContentsMargins(12, 0, 12, 0);
    containerLayout->setSpacing(10);

    flagLabel = new QLabel(this);
    flagLabel->setFixedSize(28, 28);
    flagLabel->setScaledContents(true);
    flagLabel->setText(emoji);
    flagLabel->setAlignment(Qt::AlignCenter);
    flagLabel->setObjectName("flagLabel");
    containerLayout->addWidget(flagLabel);

    lineEdit = new QLineEdit(this);
    lineEdit->setObjectName("inputField");
    lineEdit->setPlaceholderText(placeholder);
    containerLayout->addWidget(lineEdit);

    connect(lineEdit, &QLineEdit::textChanged, this, &CurrencyInput::textChanged);
}

QLineEdit* CurrencyInput::getLineEdit() const
{
    return lineEdit;
}

QWidget* CurrencyInput::getContainer() const
{
    return container;
}

void CurrencyInput::setSelectedCurrency(const QString &code, const QString &flagPath)
{
    selectedCurrency = code;

    lineEdit->blockSignals(true);
    lineEdit->setText(code);
    lineEdit->blockSignals(false);

    QPixmap pixmap(flagPath);
    if (!pixmap.isNull()) {
        flagLabel->setPixmap(pixmap.scaled(28, 28, Qt::KeepAspectRatio, Qt::SmoothTransformation));
    } else {
        flagLabel->setText(defaultEmoji);
    }
}

void CurrencyInput::clearInput()
{
    lineEdit->blockSignals(true);
    lineEdit->clear();
    lineEdit->blockSignals(false);

    selectedCurrency.clear();
    flagLabel->clear();
    flagLabel->setText(defaultEmoji);
}

void CurrencyInput::resetFlagIfNotMatching()
{

    if (!selectedCurrency.isEmpty() && lineEdit->text().toUpper() != selectedCurrency) {
        selectedCurrency.clear();
        flagLabel->clear();
        flagLabel->setText(defaultEmoji);
    }
}

QString CurrencyInput::getText() const
{
    return lineEdit->text();
}

QString CurrencyInput::getSelectedCurrency() const
{
    return selectedCurrency;
}
