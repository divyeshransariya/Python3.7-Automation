def get_prev_date(filename,date,**kwargs):
    with open(filename) as file: 
        prevdate=""
        for line in file:
            if date in line:
                prevdate = "".join(str(prevdate).split('-'))
                return prevdate
            else:
                prevdate=line.strip('\n')
        return None
