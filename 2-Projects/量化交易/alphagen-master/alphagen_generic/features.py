from alphagen.data.expression import Feature, Ref
from alphagen_qlib.stock_data import FeatureType


high = Feature(FeatureType.HIGH)
low = Feature(FeatureType.LOW)
volume = Feature(FeatureType.VOLUME)
open_ = Feature(FeatureType.OPEN)
close = Feature(FeatureType.CLOSE)
vwap = Feature(FeatureType.VWAP)
target = Ref(close, -20) / close - 1
ad = Feature(FeatureType.AD)
adosc = Feature(FeatureType.ADOSC)
adx = Feature(FeatureType.ADX)
atr = Feature(FeatureType.ATR)