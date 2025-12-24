#include "suggestionspopup.h"
#include <QHBoxLayout>
#include <QLabel>
#include <QPixmap>

SuggestionsPopup::SuggestionsPopup(QWidget *parent)
    : QListWidget(parent), currencyData(nullptr)
{
    setObjectName("suggestions");
    setVisible(false);
    setFixedHeight(0);
    setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);
    setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);

    connect(this, &QListWidget::itemClicked,
            this, &SuggestionsPopup::onItemClicked);
}

void SuggestionsPopup::setCurrencyData(CurrencyData *data)
{
    currencyData = data;
}

void SuggestionsPopup::updateSuggestions(const QString &searchText)
{
    clear();

    if (searchText.isEmpty() || !currencyData) {
        setVisible(false);
        setFixedHeight(0);
        return;
    }

    QString upperSearchText = searchText.toUpper();
    int itemCount = 0;

    const QList<QString> codes = currencyData->getAllCurrencyCodes();
    for (const QString &code : codes) {
        QString name = currencyData->getCurrencyName(code);

        if (code.startsWith(upperSearchText) || name.toUpper().startsWith(upperSearchText)) {
            createSuggestionItem(code, name);
            itemCount++;
        }
    }

    if (itemCount > 0) {
        int height = (itemCount == 1) ? 52 : 100;
        setFixedHeight(height);
        setVisible(true);
        scrollToTop();
        raise();
    } else {
        setVisible(false);
        setFixedHeight(0);
    }
}

void SuggestionsPopup::positionUnder(QWidget *targetWidget, QWidget *parentWidget)
{
    if (!targetWidget || !parentWidget) return;

    QPoint globalPos = targetWidget->mapToGlobal(QPoint(0, targetWidget->height() + 2));
    QPoint localPos = parentWidget->mapFromGlobal(globalPos);
    move(localPos.x(), localPos.y());
    setFixedWidth(targetWidget->width());
}

void SuggestionsPopup::createSuggestionItem(const QString &code, const QString &name)
{
    QListWidgetItem *item = new QListWidgetItem();
    item->setData(Qt::UserRole, code);

    QWidget *itemWidget = new QWidget();
    itemWidget->setObjectName("suggestionItem");
    itemWidget->setCursor(Qt::PointingHandCursor);

    QHBoxLayout *itemLayout = new QHBoxLayout(itemWidget);
    itemLayout->setContentsMargins(8, 8, 8, 8);
    itemLayout->setSpacing(12);

    QLabel *flagLabel = new QLabel();
    flagLabel->setFixedSize(28, 28);
    flagLabel->setScaledContents(true);
    flagLabel->setAttribute(Qt::WA_TransparentForMouseEvents);

    QString flagPath = currencyData->getFlagPath(code);
    QPixmap pixmap(flagPath);
    if (!pixmap.isNull()) {
        flagLabel->setPixmap(pixmap.scaled(28, 28, Qt::KeepAspectRatio, Qt::SmoothTransformation));
    } else {
        flagLabel->setText("💱");
        flagLabel->setAlignment(Qt::AlignCenter);
    }
    flagLabel->setStyleSheet("background-color: #e0e0e0; border-radius: 14px;");

    QLabel *textLabel = new QLabel(code + " - " + name);
    textLabel->setStyleSheet("color: #333333; font-size: 14px;");
    textLabel->setAttribute(Qt::WA_TransparentForMouseEvents);

    itemLayout->addWidget(flagLabel);
    itemLayout->addWidget(textLabel);
    itemLayout->addStretch();

    item->setSizeHint(QSize(350, 48));
    addItem(item);
    setItemWidget(item, itemWidget);
}

void SuggestionsPopup::onItemClicked(QListWidgetItem *item)
{
    QString code = item->data(Qt::UserRole).toString();
    emit currencySelected(code);

    setVisible(false);
    setFixedHeight(0);
}
