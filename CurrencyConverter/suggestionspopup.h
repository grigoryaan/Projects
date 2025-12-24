#ifndef SUGGESTIONSPOPUP_H
#define SUGGESTIONSPOPUP_H

#include <QListWidget>
#include <QWidget>
#include <QString>
#include "currencydata.h"

class SuggestionsPopup : public QListWidget
{
    Q_OBJECT

public:
    explicit SuggestionsPopup(QWidget *parent = nullptr);

    void setCurrencyData(CurrencyData *data);
    void updateSuggestions(const QString &searchText);
    void positionUnder(QWidget *targetWidget, QWidget *parentWidget);

signals:
    void currencySelected(const QString &currencyCode);

private slots:
    void onItemClicked(QListWidgetItem *item);

private:
    void createSuggestionItem(const QString &code, const QString &name);

    CurrencyData *currencyData;
};

#endif // SUGGESTIONSPOPUP_H
