import os
from urllib.parse import unquote
from dotenv import load_dotenv

load_dotenv()

CANDIDATE_API_KEY = unquote(os.environ["NEC_CANDIDATE_API_KEY"])
PLEDGE_API_KEY = unquote(os.environ["NEC_PLEDGE_API_KEY"])
SG_ID = "20260603"
SG_TYPECODES = {
    "3": "광역단체장",
    "4": "교육감",
    "5": "기초단체장",
    "6": "광역의원",
    "7": "기초의원",
    "8": "비례대표",
}

CANDIDATE_API = "http://apis.data.go.kr/9760000/PofelcddInfoInqireService/getPoelpcddRegistSttusInfoInqire"
PLEDGE_API = "http://apis.data.go.kr/9760000/ElecPrmsInfoInqireService/getCnddtElecPrmsInfoInqire"
NEC_POLICY_BASE = "https://policy.nec.go.kr"

DATA_DIR = "../data"
