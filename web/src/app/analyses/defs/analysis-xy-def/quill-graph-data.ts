import Quill, { DeltaStatic } from "quill";

export interface QuillGraphDataConfig {
  container: string
}

export default class QuillGraphData {
  private _quill: Quill;
  private _options: QuillGraphDataConfig;
  private _quillSelector: HTMLSpanElement;
  private _list: HTMLSelectElement;

  constructor(quill, options) {
    this._quill = quill;
    this._options = options;

    const contianer = document.querySelector(this._options.container);
    const button = contianer.querySelector('button');
    this._list = contianer.querySelector('select');
    this._quillSelector = contianer.querySelector('.quill-custom-select > .ql-picker-label') as HTMLSpanElement;
    this.updateCaption();
    button.addEventListener('click', (e) => {
      console.log(this._list.value);
      var selection = this._quill.getSelection(true);
      if (selection.length > 0)
        this._quill.deleteText(selection.index, selection.length);
      this._quill.insertEmbed(selection.index, 'graphdata', `${this._list.value}`);
    });
    this._list.addEventListener('change', (e) => {
      this.updateCaption();
    })
  }

  updateCaption() {
    var caption = (this._list.querySelector('option[value="' + this._list.value + '"]') as HTMLOptionElement).innerText;
    if (this._quillSelector.childNodes.item(0).nodeType !== 3)
        this._quillSelector.prepend(caption);
      else
        this._quillSelector.childNodes.item(0).textContent = caption;
  }
}


let Inline = Quill.import('blots/inline');

export class GraphDataBlot extends Inline {

  static create(value) {
    console.log("create");
    console.log(value);
    let node = super.create(value);
    node.setAttribute('contenteditable', 'false');
    node.setAttribute('spellcheck', 'false');
    var nextId = 0;
    document.querySelectorAll('.graphdata').forEach((b) => {
      var id = parseInt(b.id);
      if (nextId < id)
        nextId = id;
    });
    nextId++;

    node.setAttribute('id', nextId.toString());
    if (value !== GraphDataBlot.blotName) {
      (node as HTMLSpanElement).innerText = `{{${value}}}`;
    }
    node.addEventListener('click', function(e) {
      let blot = Quill.find(node) as GraphDataBlot;
      console.log(blot);
      let range = document.createRange();
      range.selectNodeContents(blot.domNode);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    });
    console.log(node);
    return node;
  }

  static formats(domNode: HTMLSpanElement) {
    console.log("formats");
    console.log(domNode);
    if (domNode.children.length > 0) {
      let child: HTMLElement = domNode.children.item(0) as HTMLElement;
      child.classList.forEach((name) => {
        if (name.startsWith('ql-color-'))
        child.style.color = name.replace('ql-color-', '');
      else if (name.startsWith('ql-bg-'))
        child.style.backgroundColor = name.replace('ql-bg-', '');
      else if (name.startsWith('ql-size-')) {
        let value = name.replace('ql-size-', '');
        child.style.fontSize = value === 'small' ? 'smaller' : value;
      }
      })
    }
    return domNode.getAttribute("class");
  }

  format(name, value: string) {
    console.log("format");
    console.log(name, value)
    var span = this.domNode as HTMLSpanElement;
    if (name !== this.statics.blotName || !value) {
      super.format(name, value);
    }
    if (value) {
      if (name === 'color')
        span.style.color = value;
      else if (name === 'background')
        span.style.backgroundColor = value;
      else if (name === 'size') {
        span.style.fontSize = value === 'small' ? 'smaller' : value;
        span.classList.remove(...['ql-size-normal', 'ql-size-small', 'ql-size-large']);
        span.classList.add(`ql-size-${value}`);
      }
    }
  }
}
GraphDataBlot.blotName = 'graphdata';
GraphDataBlot.tagName = 'SPAN';
GraphDataBlot.className = 'graphdata';
Quill.register(GraphDataBlot);

var BackgroundClass = Quill.import('attributors/class/background');
var ColorClass = Quill.import('attributors/class/color');
var SizeStyle = Quill.import('attributors/style/size');
Quill.register(BackgroundClass, true);
Quill.register(ColorClass, true);
Quill.register(SizeStyle, true);
