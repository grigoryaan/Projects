#include "currencyconverter.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFont>

void CurrencyConverter::setupUI()
{
    centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);

    QVBoxLayout *mainLayout = new QVBoxLayout(centralWidget);
    mainLayout->setSpacing(20);
    mainLayout->setContentsMargins(40, 30, 40, 30);
    mainLayout->setAlignment(Qt::AlignTop | Qt::AlignHCenter);

    // Title
    QLabel *titleLabel = new QLabel("Currency Converter", this);
    titleLabel->setObjectName("titleLabel");
    titleLabel->setAlignment(Qt::AlignCenter);
    QFont titleFont;
    titleFont.setPointSize(26);
    titleFont.setBold(true);
    titleLabel->setFont(titleFont);
    mainLayout->addWidget(titleLabel, 0, Qt::AlignCenter);

    mainLayout->addSpacing(10);

    // Card container
    QWidget *cardContainer = new QWidget(this);
    cardContainer->setObjectName("cardContainer");
    cardContainer->setFixedWidth(400);
    QVBoxLayout *cardLayout = new QVBoxLayout(cardContainer);
    cardLayout->setSpacing(12);
    cardLayout->setContentsMargins(25, 25, 25, 25);

    // FROM section
    QLabel *fromLabel = new QLabel("From", this);
    fromLabel->setObjectName("sectionLabel");
    cardLayout->addWidget(fromLabel);

    fromInput = new CurrencyInput("Type currency...", "💱", this);
    cardLayout->addWidget(fromInput);

    fromSuggestions = new SuggestionsPopup(centralWidget);
    fromSuggestions->setCurrencyData(currencyData);

    cardLayout->addSpacing(2);

    // AMOUNT section
    QLabel *amountLabel = new QLabel("Amount", this);
    amountLabel->setObjectName("sectionLabel");
    cardLayout->addWidget(amountLabel);

    QWidget *amountContainer = new QWidget(this);
    amountContainer->setObjectName("inputContainer");
    amountContainer->setFixedHeight(45);
    QHBoxLayout *amountContainerLayout = new QHBoxLayout(amountContainer);
    amountContainerLayout->setContentsMargins(12, 0, 12, 0);

    amountInput = new QLineEdit(this);
    amountInput->setObjectName("inputField");
    amountInput->setPlaceholderText("Enter amount...");
    amountContainerLayout->addWidget(amountInput);

    cardLayout->addWidget(amountContainer);

    cardLayout->addSpacing(2);

    // SWAP button
    QWidget *swapContainer = new QWidget(this);
    swapContainer->setFixedHeight(36);
    QHBoxLayout *swapLayout = new QHBoxLayout(swapContainer);
    swapLayout->setContentsMargins(0, 0, 0, 0);

    swapButton = new QPushButton("⇅", this);
    swapButton->setObjectName("swapButton");
    swapButton->setFixedSize(36, 36);
    swapButton->setCursor(Qt::PointingHandCursor);
    connect(swapButton, &QPushButton::clicked, this, &CurrencyConverter::onSwapClicked);
    swapLayout->addStretch();
    swapLayout->addWidget(swapButton);
    swapLayout->addStretch();

    cardLayout->addWidget(swapContainer);

    cardLayout->addSpacing(2);

    // TO section
    QLabel *toLabel = new QLabel("To", this);
    toLabel->setObjectName("sectionLabel");
    cardLayout->addWidget(toLabel);

    toInput = new CurrencyInput("Type currency...", "💰", this);
    cardLayout->addWidget(toInput);

    toSuggestions = new SuggestionsPopup(centralWidget);
    toSuggestions->setCurrencyData(currencyData);

    cardLayout->addSpacing(8);

    // Buttons
    QWidget *buttonsContainer = new QWidget(this);
    QHBoxLayout *buttonsLayout = new QHBoxLayout(buttonsContainer);
    buttonsLayout->setSpacing(12);
    buttonsLayout->setContentsMargins(0, 0, 0, 0);

    convertButton = new QPushButton("Convert", this);
    convertButton->setObjectName("convertButton");
    convertButton->setFixedHeight(46);
    convertButton->setCursor(Qt::PointingHandCursor);
    connect(convertButton, &QPushButton::clicked, this, &CurrencyConverter::onConvertClicked);
    buttonsLayout->addWidget(convertButton);

    clearButton = new QPushButton("Clear", this);
    clearButton->setObjectName("clearButton");
    clearButton->setFixedHeight(46);
    clearButton->setCursor(Qt::PointingHandCursor);
    connect(clearButton, &QPushButton::clicked, this, &CurrencyConverter::onClearClicked);
    buttonsLayout->addWidget(clearButton);

    cardLayout->addWidget(buttonsContainer);

    // Error label
    errorLabel = new QLabel(this);
    errorLabel->setObjectName("errorLabel");
    errorLabel->setAlignment(Qt::AlignCenter);
    errorLabel->setFixedHeight(40);
    errorLabel->setVisible(false);
    cardLayout->addWidget(errorLabel);

    mainLayout->addWidget(cardContainer, 0, Qt::AlignCenter);

    mainLayout->addStretch();

    // Result label
    resultLabel = new QLabel("0.00", this);
    resultLabel->setObjectName("resultLabel");
    resultLabel->setAlignment(Qt::AlignCenter);
    resultLabel->setFixedWidth(400);
    resultLabel->setFixedHeight(85);
    resultLabel->setVisible(false);
    mainLayout->addWidget(resultLabel, 0, Qt::AlignCenter);

    // Update info
    updateLabel = new QLabel("Exchange rates update in real-time", this);
    updateLabel->setObjectName("updateLabel");
    updateLabel->setAlignment(Qt::AlignCenter);
    mainLayout->addWidget(updateLabel, 0, Qt::AlignCenter);

    mainLayout->addSpacing(20);

    // Connect signals
    connect(fromInput, &CurrencyInput::textChanged, this, &CurrencyConverter::onFromTextChanged);
    connect(toInput, &CurrencyInput::textChanged, this, &CurrencyConverter::onToTextChanged);
    connect(fromSuggestions, &SuggestionsPopup::currencySelected, this, &CurrencyConverter::onFromCurrencySelected);
    connect(toSuggestions, &SuggestionsPopup::currencySelected, this, &CurrencyConverter::onToCurrencySelected);

    fromInput->getLineEdit()->installEventFilter(this);
    toInput->getLineEdit()->installEventFilter(this);

    setWindowTitle("Currency Converter QT");
    setMinimumSize(450, 700);
    resize(450, 780);
}
