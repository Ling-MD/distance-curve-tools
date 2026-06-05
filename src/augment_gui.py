import argparse, json, pandas as pd, numpy as np
from perlin_noise import perlin_noise

def generate_wave_segment(t0,t1,d0,d1,amp,n,mode):
    s = np.linspace(0, 1, n+2)
    base = d0 + (d1-d0)*s
    rng = np.random.default_rng()

    if mode=="sin":
        noise = np.sin(np.pi*s)
    elif mode=="sin_noise":
        noise = np.sin(np.pi*s)+0.5*np.sin(2*np.pi*s)
    elif mode=="gaussian":
        noise = rng.normal(0,1,size=s.shape)
    elif mode=="perlin":
        p = perlin_noise(len(s))
        noise = p / max(abs(p))
    elif mode=="spike":
        noise = rng.uniform(-1,1,len(s)) + np.sign(rng.normal(len(s)))*2
    else:
        noise = np.zeros_like(s)

    noise = noise * amp
    t = t0 + (t1-t0)*s
    d = base + noise
    return t[1:-1], d[1:-1]

def main(input_file, config_file, output_file):
    cfg = json.load(open(config_file))
    df = pd.read_csv(input_file)
    t, d = df["Time_ns"].to_numpy(), df["Distance_A"].to_numpy()

    out_t, out_d = [], []
    rng = np.random.default_rng()

    for i in range(len(t)-1):
        t0,t1 = t[i],t[i+1]
        d0,d1 = d[i],d[i+1]

        for r in cfg["regions"]:
            if r["t0"] <= t0 <= r["t1"]:
                amp,n,mode = r["amp"], r["pts"], r["mode"]
                break

        d0 += rng.uniform(-amp,amp)
        d1 += rng.uniform(-amp,amp)

        out_t.append(t0)
        out_d.append(d0)

        it,idata = generate_wave_segment(t0,t1,d0,d1,amp,n,mode)
        out_t.extend(it)
        out_d.extend(idata)

    out_t.append(t[-1])
    out_d.append(d[-1])

    a,b = cfg["global_clip"]
    out_d = np.clip(out_d, a, b)

    # save csv
    out = pd.DataFrame({"Time_ns":out_t,"Distance_A":out_d})
    out.to_csv(output_file, index=False)

    # save xvg
    xvg = output_file.replace(".csv",".xvg")
    with open(xvg,"w") as f:
        f.write("@    title \"aug curve\"\n@TYPE xy\n")
        for tt,dd in zip(out_t,out_d):
            f.write(f"{tt:.6f} {dd:.6f}\n")

    print("✅ Done!")
    print("CSV:", output_file)
    print("XVG:", xvg)


if __name__=="__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    main(args.input, args.config, args.output)
