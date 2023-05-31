#%% 匯入模組
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#%% 整理表格標題與欄位

# 讀取檔案
# (thousands = ",")可處理千分位,區隔的問題
index = pd.read_csv("index.csv",encoding = "ANSI",thousands = ",")
signal = pd.read_csv("signal.csv",encoding = "ANSI")


# 整理index表格
index.columns = ["date","price"]
index = index.drop(0,axis = 0)

# 處理千分位後轉浮點數
index["price"] = index["price"].str.replace(",","").astype(float)

# .reset_index 將索引重置
index = index.reset_index(drop = True)


# 整理signal表格
signal = signal.drop(0,axis = 0)

# 除去最下方尚未公布的空值欄位
signal = signal.dropna(axis = 0)

signal.columns = ["date","signal"]
signal["signal"] = signal["signal"].astype(float)
signal = signal.reset_index(drop = True)


#%% 將日期改為 實際公布日隔天( = 交易日期) 
# 用開盤日來尋找每月27號後(含)的工作日 = 實際公布日期

# 將日期轉為時間格式
index["date"] = pd.to_datetime(index["date"])

trade_day = []
find = 0
for i in index.index:
    
    # 大於等於27 且 該月沒找到
    if index.iloc[i,0].day>= 27 and find!= index.iloc[i,0].month:
        
        # 以索引(i+1)直接改為交易日期(下一個開盤日)
        trade_day.append([index.iloc[i+1,0]])
        find = index.iloc[i,0].month
        
    # 前一個月沒找到(因為一月或二月底很常遇到春節或連假、所以可能會有隔月才公布的情況)
    elif find!= 0 and (find == index.iloc[i,0].month-2 \
                      or find == index.iloc[i,0].month-2+12):
        trade_day.append([index.iloc[i+1,0]])
        find = index.iloc[i,0].month-1 

# 一月的分數是二月底才公布的，所以時間要再往後挪一個月
signal["date"] = pd.DataFrame(trade_day[1:],columns = ["date"])


#%% 將五種燈號貼標籤

# 以分數小至大排序
signal = signal.sort_values("signal")

# 建立區間 使用cut()函數
score = [0,17,23,32,38,46]
labels = [i for i in range(5)]
signal["signal"] = pd.cut(signal["signal"], bins = score, labels = labels) 

# 恢復順序
signal = signal.sort_values("date")


#%% 計算各策略報酬率

"""
決策1:長期持有不賣
"""

# 建立"日報酬"率變化 pct_change()
# 計算方式 = (今日價格-昨日價格)/昨日價格
index["strategy1"] = index["price"].pct_change()


"""
決策2:紅賣藍買
遇到第一顆4分、第一顆0分時做交易
"""

# 尋找需要做交易的燈號時間
meet = 0
strategy2 = []
for i,signal_ in enumerate(signal["signal"]):
    # 遇紅燈前只會跑這裡(找紅燈)
    if meet == 0:
        if signal_ == 4:
            strategy2.append([signal.iloc[i,0],"sell"])
            meet = 1
    # 遇紅燈後只會跑這裡(找藍燈)
    elif meet == 1:
        if signal_ == 0:
            strategy2.append([signal.iloc[i,0],"buy"])
            meet = 0
strategy2 = pd.DataFrame(strategy2,columns = ["date","strategy2"])

# 把策略2的買賣日放在index表裡
index = pd.merge(index, strategy2, on = "date",how = "outer")

# 將報酬率對應至買賣區間
meet = 0
for i in index.index:
    
    # 持有部位時跑這裡
    if meet == 0:
        if index.iloc[i,3] == "sell":
            index.iloc[i,3] = index.iloc[i,2]
            # 遇到要賣出時讓meet = 1
            meet = 1
        else:
            index.iloc[i,3] = index.iloc[i,2]
    
    # 空手時跑這裡
    elif meet == 1:
        if index.iloc[i,3] == "buy":
            index.iloc[i,3] = 0
            # 遇到要買入時讓meet = 0
            meet = 0
        else:
            index.iloc[i,3] = 0

# 將報酬率轉成浮點數
index["strategy2"] = index["strategy2"].astype(float)


"""
決策3:紅賣藍買(藍燈分五批進場 一次加碼20%)
遇到第一顆4分、前五顆0分時做交易
"""

# 尋找需要做交易的燈號"公布日期"
meet = 0
strategy3 = []
blue = []
for i,signal_ in enumerate(signal["signal"]):
    
    # 遇紅燈前只會跑這裡(找紅燈)
    if meet == 0:
        if signal_ == 4 :
            strategy3.append([signal.iloc[i,0],"sell"])
            meet = 1
    
    # 遇紅燈後只會跑這裡(找藍燈)
    elif meet == 1:
        if len(blue) == 5:
            blue = []
            meet = 0
        elif signal_ == 0:
            strategy3.append([signal.iloc[i,0],"buy"])
            blue.append(signal.iloc[i,0])
strategy3 = pd.DataFrame(strategy3,columns = ["date","strategy3"])

# 把策略3的買賣日放在index表裡
index = pd.merge(index, strategy3, on = "date",how = "outer")

# 將報酬率對應至買賣區間
meet = 0
buy = [0]*5 # 回測初期為100%買入、使串列長度為5
for i in index.index:
    
    # 持有部位時跑這裡
    if meet == 0:
        if index.iloc[i,4] == "sell":
            index.iloc[i,4] = index.iloc[i,2]*(len(buy)*0.2)
            # 遇到要賣出時讓meet = 1 、 將buy串列清空
            meet = 1
            buy = []
        else:
            if index.iloc[i,4] == "buy":
                buy.append(i)
            index.iloc[i,4] = index.iloc[i,2]*(len(buy)*0.2)
    
    # 空手時跑這裡
    elif meet == 1:
        if index.iloc[i,4] == "buy":
            index.iloc[i,4] = 0
            # 遇到要買入時讓meet = 0
            meet = 0
            buy.append(i)
        else:
            index.iloc[i,4] = 0

# 將報酬率轉成浮點數
index["strategy3"] = index["strategy3"].astype(float)


"""
決策4:搭配部位配置：50%策略1 + 50%策略3
"""

index["strategy4"] = (index["strategy1"]+index["strategy3"])/2


#%% 視覺化

# 設定字體為"微軟正黑體"
plt.rcParams["font.family"] = "Microsoft JhengHei"
# 設定正常顯示正負號
plt.rcParams["axes.unicode_minus"] = False


"""
紅藍燈對應至指數走勢圖
"""

# 資料合併 pd.merge(on = "key欄位名稱" , how = "inner"(交集))
signal_scatter = pd.merge(index, signal, on = "date",how = "inner")
m1 = signal_scatter["signal"] == 0
m2 = signal_scatter["signal"] == 4
signal_blue = signal_scatter[m1]
signal_red = signal_scatter[m2]

# 畫圖
plt.figure(figsize = (20,12),facecolor = "gainsboro")
plt.plot(index["date"],index.loc[:,"price"],"-",c = "black",label = "加權指數",alpha = 0.4)
plt.scatter(signal_blue["date"],signal_blue["price"],c = "mediumblue",label = "藍燈",s = 50, zorder = 5)
plt.scatter(signal_red["date"],signal_red["price"],c = "firebrick",label = "紅燈",s = 80, zorder = 5)
plt.legend(loc = "upper left",fontsize = 20)
plt.ylabel("加      \n權      \n指      \n數      ",fontsize = 20,rotation = 0)
plt.yticks(fontsize = 30)
plt.xticks(fontsize = 30)
plt.title("紅藍燈對應至加權指數之時間點",fontsize = 20)
plt.savefig("all.png")
plt.show()


"""
各策略示意圖
"""

def draw_strategy(table,size,per,name,title):
    A = pd.DataFrame([index.iloc[0,0],"buy"]).T
    A.columns = ["date",name]
    new_table = pd.concat([A,table], axis = 0)
    new_table = pd.merge(new_table, index.iloc[:,:2], on = "date")
    buy = new_table[new_table[name] == "buy"]
    sell = new_table[new_table[name] == "sell"]
    plt.figure(figsize = (10,8),facecolor = "gainsboro")
    plt.plot(index["date"],index.loc[:,"price"],"-",c = "black",label = "加權指數",alpha = 0.4)
    plt.scatter(buy["date"],buy["price"],c = "mediumblue",label = "Buy"+per,s = size, zorder = 5)
    plt.scatter(sell["date"],sell["price"],c = "firebrick",label = "Sell",s = 150, zorder = 5)
    plt.legend(loc = "upper left",fontsize = 16)
    plt.ylabel("加      \n權      \n指      \n數      ",fontsize = 15,rotation = 0)
    plt.yticks(fontsize = 15)
    plt.xticks(fontsize = 15)
    plt.title(title,fontsize = 20)
    plt.savefig(name+".png")
    plt.show()

draw_strategy(None,150,"","strategy1","策略一")
draw_strategy(strategy2,150,"","strategy2","策略二")
draw_strategy(strategy3,50,"(20%)","strategy3","策略三")


"""
計算累積報酬率+畫走勢圖
"""

def draw_return(index,title,name):
    plt.figure(figsize = (20,10),facecolor = "gainsboro")
    plt.plot(index, tr_s1, label = "策略1：長期持有", alpha = 0.8)
    plt.plot(index, tr_s2, label = "策略2：紅燈賣 藍燈買", alpha = 0.8)
    plt.plot(index, tr_s3, label = "策略3：紅燈賣 藍燈分5次進場", alpha = 0.8)
    plt.plot(index, tr_s4, label = "策略4：策略1(50%)+策略3(50%)", alpha = 0.8)
    plt.ylabel("報      \n酬      \n率      \n(%)      ", fontsize = 20, rotation = 0)
    plt.yticks(fontsize = 30)
    plt.xticks(fontsize = 30)
    plt.legend(fontsize = 20)
    plt.title(title, fontsize = 20)
    plt.savefig(name+".png")
    plt.show()


"（1）1984/1/5-2023/4/12 "

# 計算累積報酬率 cumprod()函數
tr_s1 = ((index["strategy1"]+1).cumprod()-1)*100
tr_s2 = ((index["strategy2"]+1).cumprod()-1)*100
tr_s3 = ((index["strategy3"]+1).cumprod()-1)*100
tr_s4 = ((index["strategy4"]+1).cumprod()-1)*100

# 畫圖
draw_return(index["date"],"1984年至今之報酬率","1984")


"（2）1990/06/29-2023/4/12 "

# 報酬率是從6/30開始計算，所以index是1868
tr_s1 = ((index["strategy1"][1868:] + 1).cumprod() - 1)*100
tr_s2 = ((index["strategy2"][1868:] + 1).cumprod() - 1)*100
tr_s3 = ((index["strategy3"][1868:] + 1).cumprod() - 1)*100
tr_s4 = ((index["strategy4"][1868:] + 1).cumprod() - 1)*100

# 畫圖
draw_return(index["date"][1868:],"1990年至今之報酬率","1990")


#%% 獲取各時間段之最終報酬率

contrast = []
def last_return(a,b,name):
    global tr_s1,tr_s2,tr_s3,tr_s4
    strategy = [str(name)]
    tr_s1 = ((index["strategy1"][a:b] + 1).cumprod() - 1)*100
    tr_s2 = ((index["strategy2"][a:b] + 1).cumprod() - 1)*100
    tr_s3 = ((index["strategy3"][a:b] + 1).cumprod() - 1)*100
    tr_s4 = ((index["strategy4"][a:b] + 1).cumprod() - 1)*100
    tr = [tr_s1,tr_s2,tr_s3,tr_s4]
    for i in tr:
        strategy.append(round(i.iloc[-1],2))
    return strategy

# 取得"完整"週期循環之買賣時間索引
cycle = strategy2.copy()
cycle = pd.merge(index.iloc[:,:2],cycle,on = "date",how = "outer")
cycle = cycle.dropna(subset = "strategy2",axis = 0)
cycle = [i for i in cycle.index]
# 刪除週期不完整之索引
del cycle[0]


# 計算各週期報酬率 轉成CSV檔
contrast.append(last_return(None,None,"1984")) 
contrast.append(last_return(1868,None,"1990")) 
for i in range(0,len(cycle)-1,2): #  == range(0, 10, 2)
    name = "cycle"+str(int(i/2+1))
    contrast.append(last_return(cycle[i],cycle[i+2],name))
contrast = pd.DataFrame(contrast).T
contrast.columns = contrast.iloc[0,:]
contrast = contrast.drop(0,axis = 0)
contrast.index = ["策略1","策略2","策略3","策略4"]
contrast.to_csv("contrast.csv")
