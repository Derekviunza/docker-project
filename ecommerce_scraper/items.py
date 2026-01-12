import scrapy


class ProductItem(scrapy.Item):
    source = scrapy.Field()     # jumia | masoko | phoneplacekenya | laptopclinic
    title = scrapy.Field()
    price = scrapy.Field()      # float (KES)
    currency = scrapy.Field()   # "KES"
    url = scrapy.Field()
    match_key = scrapy.Field()
    scraped_at = scrapy.Field() # ISO timestamp UTC
