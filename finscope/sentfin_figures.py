"""Render aggregate SEntFiN figures, without loading models or raw corpus."""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metrics',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    m=json.loads(args.metrics.read_text(encoding='utf-8'))
    args.output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(7.6,4.3),layout='constrained')
    x=np.arange(2);width=.34
    for i,(method,name,color) in enumerate([('finbert','Pinned FinBERT','#2266AA'),('lexicon','LM dictionary','#CC7733')]):
        values=[m[method]['accuracy'],m[method]['macro_f1']]
        bars=ax.bar(x+(i-.5)*width,values,width,label=name,color=color)
        ax.bar_label(bars,labels=[f'{v:.3f}' for v in values],padding=4)
    ax.set(xticks=x,xticklabels=['Accuracy','Macro-F1'],ylim=(0,1),ylabel='Score (0–1)',
           title=f'SEntFiN single-entity headlines (n={m["paired"]})')
    ax.legend(loc='upper right');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.savefig(args.output/'sentfin_comparison.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4.3),layout='constrained')
    maximum=max(max(row) for method in ['finbert','lexicon'] for row in m[method]['rows_reference_columns_prediction'])
    for ax,method,name in zip(axes,['finbert','lexicon'],['Pinned FinBERT','LM dictionary']):
        matrix=np.array(m[method]['rows_reference_columns_prediction'])
        ax.imshow(matrix,cmap='Blues',vmin=0,vmax=maximum)
        ax.set(xticks=range(3),yticks=range(3),xticklabels=['Positive','Neutral','Negative'],yticklabels=['Positive','Neutral','Negative'],xlabel='Predicted label',ylabel='Original reference label',title=name)
        for i in range(3):
            for j in range(3):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>maximum*.55 else '#172B4D',fontsize=13)
    fig.suptitle(f'SEntFiN confusion matrices: counts, same {m["paired"]} titles')
    fig.savefig(args.output/'sentfin_confusion.png',dpi=180);plt.close(fig)


if __name__=='__main__':main()
