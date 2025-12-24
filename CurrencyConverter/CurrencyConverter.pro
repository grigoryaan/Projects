QT += core gui widgets network

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

CONFIG += c++17

TARGET = CurrencyConverter
TEMPLATE = app

SOURCES += \
    main.cpp \
    currencyconverter.cpp \
    currencyconverter_ui_setup.cpp \
    currencyconverter_ui_styles.cpp \
    currencyconverter_slots.cpp \
    currencyconverter_helpers.cpp \
    currencydata.cpp \
    networkmanager.cpp \
    suggestionspopup.cpp \
    currencyinput.cpp

HEADERS += \
    currencyconverter.h \
    currencydata.h \
    networkmanager.h \
    suggestionspopup.h \
    currencyinput.h

RESOURCES += \
    resources.qrc

# Default rules for deployment
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target
