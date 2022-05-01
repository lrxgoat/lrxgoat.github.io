in_f= open("./DOT/have_dot.txt","r")

while True:
    line = in_f.readline()
    if not line:break
    ip = line.split(",")[0]
    domain = line.split(",")[1]

    temp = "<tr>" + "<td>" + ip + "<td/>"