# humpday_day_trader
For the stock pick of the week


# Stetup
1. Setup Prefect Cloud
The general architecure here is that we just use prefect cloud to remotely monitor what is running. The workers are actually local, in order to simplify a lot of CI/CD stuff (local variables, local code, etc.). Prefect allows for a simple workflow orchestraton and for us to easily schedule when things run.

2. Set up pyenv
Any 3.11 should be fine. Once that is set up:
```bash
pip install -r requirements.txt
```
3. Start a prefect work-pool and worker
```bash
prefect work-pool start humpday
```
Then in [screen](https://www.gnu.org/software/screen/) or some equivalent, in the repo directory and with the right pyenv
```bash
prefect worker start --pool humpday
```
Exit the screen. Now, when you deploy flows to the humpday work-pool, it is this local worker that will run them.