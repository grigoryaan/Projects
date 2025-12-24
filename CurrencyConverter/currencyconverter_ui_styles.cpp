#include "currencyconverter.h"

void CurrencyConverter::styleApplication()
{
    setStyleSheet(R"(
        QMainWindow {
            background-color: #f5f5f5;
        }

        #titleLabel {
            color: #2c3e50;
        }

        #cardContainer {
            background-color: white;
            border-radius: 16px;
            border: 1px solid #e0e0e0;
        }

        #sectionLabel {
            color: #7f8c8d;
            font-size: 12px;
            font-weight: 500;
        }

        #inputContainer {
            background-color: #fafafa;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
        }

        #inputContainer:focus-within {
            border-color: #3498db;
        }

        #inputField {
            background-color: transparent;
            border: none;
            color: #333333;
            font-size: 14px;
            padding: 0px;
        }

        #inputField::placeholder {
            color: #999999;
        }

        #flagLabel {
            background-color: #e0e0e0;
            border-radius: 14px;
            font-size: 18px;
        }

        #swapButton {
            background-color: #9b59b6;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 20px;
            font-weight: bold;
        }

        #swapButton:hover {
            background-color: #8e44ad;
        }

        #convertButton {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
        }

        #convertButton:hover {
            background-color: #2980b9;
        }

        #clearButton {
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
        }

        #clearButton:hover {
            background-color: #c0392b;
        }

        #suggestions {
            background-color: white;
            border: 2px solid #3498db;
            border-radius: 8px;
            padding: 4px;
        }

        #suggestions::item {
            color: #333333;
            padding: 0px;
            margin: 2px;
            border-radius: 6px;
        }

        #suggestions::item:hover {
            background-color: #e8f4f8;
        }

        #suggestions::item:selected {
            background-color: #d6eaf8;
        }

        QScrollBar:vertical {
            background-color: transparent;
            width: 6px;
            margin: 2px;
        }

        QScrollBar::handle:vertical {
            background-color: #3498db;
            border-radius: 3px;
            min-height: 20px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #2980b9;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }

        #resultLabel {
            background-color: #2ecc71;
            color: white;
            border-radius: 12px;
            font-size: 32px;
            font-weight: bold;
        }

        #errorLabel {
            background-color: #e74c3c;
            color: white;
            border-radius: 8px;
            font-size: 13px;
            font-weight: bold;
        }

        #updateLabel {
            color: #95a5a6;
            font-size: 13px;
        }
    )");
}
