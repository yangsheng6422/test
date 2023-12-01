from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
import talib

class MacdTrend(CtaTemplate):
    """"""

    author = "松鼠宽客"

    NT=10 #跨周期参数
    TT=5
    XX=2
    TRS=40 #移动止损幅度
    Lots=1 #手数

    bars=[]
    ntMA=0
    MACD=0
    atr_value = 0
    atr2=0
    dev=0
    highPrice=0
    lowPrice=0
    highma=0
    lowma=0
    nextTrend=0
    maxLowPrice=0
    trend=0
    minHighPrice=0
    up=0
    down=0
    arrowUp=0
    arrowDown=0
    atrLow=[]
    atrHigh=[]
    ht=0
    SendOrderThisBar=False
    out_range=0
    open_bar=0
    HighAfterEntry=0
    LowAfterEntry=0
    liQKA=0
    DliqPoint=0
    KliqPoint=0

    fsDonchianHi=0
    fsDonchianLo=0

    parameters = ["NT", "TT", "XX","TRS","Lots"]
    variables = ["SendOrderThisBar","out_range","open_bar","HighAfterEntry","LowAfterEntry",
                "liQKA","DliqPoint","KliqPoint","atr_value","atr2","dev","highPrice","lowPrice",
                "highma","nextTrend","maxLowPrice","trend","minHighPrice","up","down","arrowUp",
                "arrowDown","atrLow","atrHigh","ht","ntMA","fsDonchianHi","fsDonchianLo","MACD"
                ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg5 = BarGenerator(self.on_bar,5,self.on_5min_bar)
        self.am5 = ArrayManager()
        self.bgNT = BarGenerator(self.on_bar,self.NT,self.on_15min_bar)
        self.amNT = ArrayManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(50)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg5.update_tick(tick)

    def on_bar(self, bar: BarData):
        """收到Bar推送（必须由用户继承实现）"""
        # 基于NT分钟判断趋势过滤，因此先更新
        self.bgNT.update_bar(bar)
        # 基于5分钟判断
        self.bg5.update_bar(bar)

    def on_5min_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.cancel_all()
        am5 = self.am5
        am5.update_bar(bar)
        if not am5.inited:
            return

        self.fsDonchianHi  = max(am5.high_array[-20 - 1:-2]) 
        self.fsDonchianLo  = min(am5.low_array[-20 - 1:-2])  

        atr_array = am5.atr(50,array=True)
        self.atr_value = atr_array[-1]

        self.atr2 = self.atr_value/2
        self.dev = self.TT*self.atr2

        self.highPrice = am5.high_array[-self.XX - 1]
        self.lowPrice = am5.low_array[-self.XX - 1]  
        self.highma = talib.SMA(am5.high_array, self.XX)[-1]
        self.lowma = talib.SMA(am5.low_array, self.XX)[-1]

        if self.nextTrend == 1 :
            self.maxLowPrice=max(self.lowPrice,self.maxLowPrice)
            if self.highma < self.maxLowPrice and am5.close_array[-1] < am5.low_array[-2] :
                self.trend= 1
                self.nextTrend = 0
                self.minHighPrice = self.highPrice
        else :
            self.minHighPrice=min(self.highPrice, self.minHighPrice)
            if  self.lowma > self.minHighPrice and am5.close_array[-1] > am5.high_array[-2] :
                self.trend = 0
                self.nextTrend = 1
                self.maxLowPrice = self.lowPrice

        if self.trend == 0 :
            if self.trend != 0 :
                self.up= self.down
                self.arrowUp= self.up - self.atr2
            else :
                self.up =  max(self.maxLowPrice, self.up)
            self.atrHigh.append(self.up + self.dev)
            self.atrLow.append(self.up - self.dev)
        else :
            if self.trend != 1 :
                self.down= self.up
                self.arrowDown= self.down + self.atr2
            else:
                self.down= min(self.minHighPrice, self.down)
            self.atrHigh.append(self.down + self.dev)
            self.atrLow.append(self.down - self.dev)


        self.ht = self.up if self.trend == 0 else self.down
        if len(self.atrHigh)<2 or len(self.atrLow)<2:
           return
        cond1=am5.high_array[-1]>=self.atrHigh[-2] and am5.close_array[-1] > self.ntMA  and  self.MACD > 0
        cond2=am5.low_array[-1]<=self.atrLow[-2] and am5.close_array[-1] < self.ntMA and  self.MACD < 0
        if self.trend==0:
            if self.pos==0 and cond1==True :
                #self.buy(bar.close_price, self.Lots)
                self.buy(max(self.atrHigh[-2],bar.open_price), self.Lots,stop=True) #
                self.SendOrderThisBar=True
                self.open_bar=0 #开仓历时
                self.out_range=self.TRS
                self.LowAfterEntry = bar.low_price #保存开多价格
        else :
            if self.pos==0 and cond2==True :
                #self.short(bar.close_price, self.Lots)
                self.short(min(self.atrLow[-2],bar.open_price),self.Lots,stop=True) #
                self.SendOrderThisBar=True
                self.open_bar=0 #开仓历时
                self.out_range=self.TRS
                self.HighAfterEntry = bar.high_price  #保存开空价格

        if (self.pos >0) : #多头持仓的情况下
            Dcond_outTrs=am5.close_array[-1]>self.fsDonchianHi and am5.close_array[-2]<self.fsDonchianHi
            if(Dcond_outTrs and self.SendOrderThisBar==True) :
                self.out_range=self.TRS*0.8
                self.SendOrderThisBar=False

        if (self.pos <0) : #空头持仓的情况下
            Kcond_outTrs=am5.close_array[-1]<self.fsDonchianLo and am5.close_array[-2]>self.fsDonchianLo
            if(Kcond_outTrs and self.SendOrderThisBar==True) :
                self.out_range=self.TRS*0.8
                self.SendOrderThisBar=False

        if(self.pos!=0):
            #持续更新最低最高价
            if self.open_bar == 0 :
                self.HighAfterEntry = bar.high_price  #保存开空价格
                self.LowAfterEntry = bar.low_price #保存开多价格
            elif self.open_bar>0 :
                self.HighAfterEntry = min(self.HighAfterEntry,bar.high_price) # 空头止损，更新最低的最高价
                self.LowAfterEntry = max(self.LowAfterEntry,bar.low_price)    # 多头止损，更新最高的最低价
            self.open_bar=self.open_bar+1
        if(self.pos==0) :  # 自适应参数默认值；
            self.liQKA = 1
        else:				 #当有持仓的情况下，liQKA会随着持仓时间的增加而逐渐减小，即止损止盈幅度乘数的减少。
            self.liQKA = self.liQKA - 0.1
            self.liQKA = max(self.liQKA,0.3)
        if(self.pos>0 and self.open_bar>=1):
            self.DliqPoint = self.LowAfterEntry - (bar.open_price*(self.out_range/1000))*self.liQKA #经过计算，这根吊灯出场线会随着持仓时间的增加变的越来越敏感；
        elif(self.pos<0 and self.open_bar>=1):
            self.KliqPoint = self.HighAfterEntry + (bar.open_price*(self.out_range/1000))*self.liQKA #经过计算，这根吊灯出场线会随着持仓时间的增加变的越来越敏感；
        #多头平仓
        if (self.pos>0 and self.open_bar>=1) and bar.low_price<self.DliqPoint:
                print("平多")
                self.sell(min(self.DliqPoint,bar.low_price), self.Lots, stop=True)
        #空头平仓
        if (self.pos<0 and self.open_bar>=1) and bar.high_price>self.KliqPoint:
                print("平空")
                self.cover(max(self.KliqPoint,bar.high_price), self.Lots, stop=True)
                

        self.put_event()

    def on_15min_bar(self, bar: BarData):
        self.amNT.update_bar(bar)
        if not self.amNT.inited:
            return
        #跨周期均线
        ma=self.amNT.sma(60,array=True)
        self.ntMA=ma[-1]
        self.macd_macd, self.macd_signal, self.macd_hist = self.amNT.macd(12,26,9,array=True)

        self.MACD=self.macd_macd[-1]
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass
