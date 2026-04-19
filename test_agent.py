import json
import logging
from datetime import date
from config.settings import load_config, CompanyData
from agents.huggingface_agents import ThreeAgentSystem

logging.getLogger().setLevel(logging.CRITICAL)

config = load_config()
system = ThreeAgentSystem(config.agent)
system.initialize()

company = CompanyData(
    ticker="NVDA", 
    company_name="Nvidia", 
    sector="Tech", 
    industry="Semis", 
    market_cap=1e12, 
    report_date=date.today()
)
res = system.bear_agent.analyze(company, [], lambda x: x, lambda x: x)
print("RAWRESPONSE:")
print(res.raw_response)
print("ENDRAWRESPONSE")
print("PARSED:")
print(res)
print("ENDPARSED")
