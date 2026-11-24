// BestPhotoBefore.ets - 他日最佳页面
import router from '@ohos.router';

interface PhotoItem {
  name: string;
  url: string;
}

@Entry
@Component
struct BestPhotoBefore {
  @State photoList: PhotoItem[] = [];

  private readonly OBS_BASE_URL: string = 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/bestphotobefore/';

  aboutToAppear(): void {
    this.loadPhotoList();
  }

  loadPhotoList(): void {
    const fileNames: string[] = [
      '0103.jpg',
      '0205.JPG',
      '0406.jpg',
      '0506.jpg',
      '0509.jpg',
      '0615.jpg',
      '0616.jpg',
      '0627.JPG',
      '0628.jpg',
      '0629.jpg',
      '0701.jpg'
    ];

    const tempList: PhotoItem[] = [];
    for (let i = 0; i < fileNames.length; i++) {
      const name: string = fileNames[i];
      tempList.push({
        name: name,
        url: this.OBS_BASE_URL + encodeURIComponent(name)
      });
    }
    this.photoList = tempList;
  }

  build() {
    Column() {
      Row() {
        Image($r('sys.symbol.arrow_left'))
          .width(24)
          .height(24)
          .onClick(() => router.back())
        Text('他日最佳')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .margin({ left: 16 })
        Blank()
      }
      .width('100%')
      .height(56)
      .padding({ left: 16, right: 16 })
      .backgroundColor(Color.White)

      Row() {
        Text(`共 ${this.photoList.length} 张照片`)
          .fontSize(14)
          .fontColor('#666666')
      }
      .width('100%')
      .padding(16)

      if (this.photoList.length === 0) {
        Column() {
          Text('📷')
            .fontSize(60)
            .fontColor('#CCCCCC')
          Text('暂无照片')
            .fontSize(16)
            .fontColor('#999999')
            .margin({ top: 16 })
        }
        .width('100%')
        .height('60%')
        .justifyContent(FlexAlign.Center)
      } else {
        Scroll() {
          Grid() {
            ForEach(this.photoList, (photo: PhotoItem) => {
              GridItem() {
                Column() {
                  Image(photo.url)
                    .width('100%')
                    .aspectRatio(1)
                    .borderRadius(8)
                    .objectFit(ImageFit.Cover)
                    .backgroundColor('#F0F0F0')
                  Text(photo.name.substring(0, photo.name.lastIndexOf('.')))
                    .fontSize(12)
                    .fontColor('#666666')
                    .maxLines(1)
                    .textOverflow({ overflow: TextOverflow.Ellipsis })
                    .margin({ top: 4 })
                }
              }
              .padding(4)
            })
          }
          .columnsTemplate('1fr 1fr 1fr')
          .columnsGap(8)
          .rowsGap(8)
          .padding({ left: 12, right: 12 })
        }
        .width('100%')
        .layoutWeight(1)
        .scrollBar(BarState.Auto)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FAFAFA')
  }
}