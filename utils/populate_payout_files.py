import os, logging
from collections import defaultdict
from datetime import datetime, timedelta,date
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')
PAYOUT_SUFFIX = ".payout"

def sanity_check(payout_file, trading_date_file, matched_with="",**kwargs):
    with open(trading_date_file,"r") as f1:
        with open(payout_file, "r") as f2:
            _seg1 = f1.readline().strip()
            _seg2 = f2.readline().strip()
            assert _seg1.strip("\n") == matched_with, "Expected segment %s recieved %s!.."%(matched_with, _seg1)
            assert _seg2.strip("\n") == matched_with, "Expected segment %s recieved %s!.."%(matched_with, _seg2)
    return True

# def get_exchange_name(exchang_id):
#     if exchang_id == "NseFO":
#         return "nse_fo"
#     if exchang_id == "NseCM":
#         return "nse_cm"
#     if exchang_id == "NseCD":
#         return "nse_cd"
#     if exchang_id == "BseCD":
#         return "bse_cd"
#     if exchang_id == "SgxFO":
#         return "sgx_fo"
#     raise ValueError("Invalid exchange id %s! .. exiting.."%exchang_id)

def get_last_thrusday(Date):
    from dateutil.relativedelta import relativedelta, TH
    return Date + relativedelta(day=31, weekday=TH(-1))

def search_date(input_file, date):
    with open(input_file, "r") as fin:
        return date in fin.read()

def string_to_date(date:str):
    return date, datetime.strptime(date, "%Y-%m-%d").date()

def extract_last_line(file_path, mode="r"):
    with open(file_path, mode) as fin:
        lines = fin.readlines()
    return lines[-1]

def populate_payout_files(payout_file_path):
    validate_seg_ids=set(['SgxFO', 'NseFO', 'BseCD', 'NseCM', 'NseCD'])
    files=[]
    date_regex = '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}$'    ## date regex *YYYY-MM-DD || u can use >>> grep -o "....-..-..$"
    for exchange_segment in validate_seg_ids:
        file_path, _ = os.path.split(payout_file_path)
        payout_file = os.path.join(file_path, get_exchange_name(exchange_segment) + PAYOUT_SUFFIX)
        if not os.path.exists(payout_file): ## If given payout file don't exist then create one
            logging.info("created %s"%payout_file)
            os.system('echo ' + exchange_segment + f' > {payout_file}')
            os.system("grep " + f"'{exchange_segment}' {payout_file_path} | sort | grep -o '{date_regex}' >> {payout_file}")
            logging.debug("generated payout file %s"%payout_file)
            files.append(payout_file)
    return files

def generate_payout_dates_sgx_fo(payout_file_path, trading_date_file, year : int =2020) -> list:
    return generate_payout_dates_cm_fo(payout_file_path, trading_date_file, "SgxFO", year)

def generate_payout_dates_nse_fo(payout_file_path, trading_date_file, year : int =2020) -> list:
    return generate_payout_dates_cm_fo(payout_file_path, trading_date_file, "NseFO", year)

def generate_payout_dates_nse_cm(payout_file_path, trading_date_file, year : int =2020) -> list:
    return generate_payout_dates_cm_fo(payout_file_path, trading_date_file, "NseCM", year)

def generate_payout_dates_cm_fo(payout_file_path, trading_date_file, expected_seg, year : int =2020) -> list:
    sanity_check(payout_file=payout_file_path, trading_date_file=trading_date_file, matched_with=expected_seg)
    _, dt = string_to_date(extract_last_line(payout_file_path).strip("\n"))
    first_date_of_month=[]  ## Stroing YYYY-MM-01 dates till given year
    yy,month = (dt.year+1,1) if dt.month == 12 else (dt.year, dt.month+1)
    while yy <= year:
        first_date_of_month += [date(yy, month, 1)]
        if month == 12:
            yy += 1
        month = (month%12) + 1

    result=[]
    for i in first_date_of_month:
        last_th_day=get_last_thrusday(i) ## Last thrush day in datetime.date
        while last_th_day > i:  ## checking last thrus day is holiday or not
            last_th_day_ftime = last_th_day.strftime("%Y-%m-%d\n")
            if not search_date(trading_date_file, last_th_day_ftime):
                last_th_day -= timedelta(days=1)
            else:
                result.append(last_th_day_ftime)
                break
    logging.debug("appended dates: %s"%result)
    with open(payout_file_path,"a") as fout:
        fout.writelines(result)
    return result

def generate_payout_dates_cd(payout_file_path, trading_date_file, expected_seg="NseCD", year=2020):  ##Generate future payout dates till given year
    sanity_check(payout_file= payout_file_path, trading_date_file=trading_date_file, matched_with=expected_seg)
    nse_cd_dates = defaultdict(dict)    ## dict(year:(dict(month:[list of business days])))
    _, last_dt = string_to_date(extract_last_line(payout_file_path).strip("\n"))

    with open(trading_date_file, "r") as f:
        f.readline()    ##Skipping first line
        for date in f:
            date = date.strip("\n") ## removing extra "\n" from date
            _, dt = string_to_date(date)
            if dt > last_dt:   ## adding all those date which is greter than last date in given payout file
                _year, month, day = date.split("-")
                month_dict = nse_cd_dates[_year] ## month -> [list of trading days]
                if month not in month_dict:
                    month_dict[month]=[day]
                else:
                    month_dict[month]+=[day]
                nse_cd_dates[_year].update(month_dict)

    result=[]
    with open(payout_file_path, "a") as fout:
        for _year in nse_cd_dates:
            if int(_year)<= year:
                for month in nse_cd_dates[_year]:
                    if int(month)>last_dt.month:    ## Add date Only if month is greater than last appended date
                        fout.write(_year + "-" + month + "-" + nse_cd_dates[_year][month][-3] + "\n")
                        result+=[_year + "-" + month + "-" + nse_cd_dates[_year][month][-3]]
    logging.debug("appended dates: %s"%result)
    return result

def generate_payout_dates_bse_cd(payout_file_path, trading_date_file, year=2020):  ##Generate future payout dates till given year
    return generate_payout_dates_cd(payout_file_path, trading_date_file, "BseCD", year)

generate_payout_dates_bse_cd("/home/divyesh/git/tools/etc/trading_dates/bse_cd.payout", "/home/divyesh/git/tools/etc/trading_dates/bse_cd.dates")
######## UASGE ########
"""
seg = populate_payout_files("<path to payOutDate.csv")
generate_payout_dates_nse_fo("<path to nse_fo.payout",
    "<path to nse_fo.dates")
generate_payout_dates_nse_cm("<path to nse_cm.payout",
    "<path to nse_cm.dates")
generate_payout_dates_sgx_fo("<path to sgx_fo.payout",
    "<path to sgx_fo.dates")
generate_payout_dates_cd("<path to nse_cd.payout",
    "<path to nse_cd.dates")
"""